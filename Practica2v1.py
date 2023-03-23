"""
Solution to the one-way tunnel
"""
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 0
NORTH = 1

NCARS = 100
NPED = 10
TIME_CARS = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRGIAN = (30, 10) # normal 1s, 0.5s


class Monitor():

    def __init__(self):
        self.mutex = Lock()
        self.numCnorte=Value('i',0)#numero de coches norte pasando
        self.numCsur=Value('i',0)#numero de coches sur pasando
        self.numP = Value('i',0)#numero de peatones pasando
        self.VCS = Condition(self.mutex)
        self.VCN = Condition(self.mutex)
        self.VP = Condition(self.mutex)
    """

    Invariante
    numCnorte >= 0
    numCsur >= 0
    numP >= 0
    numCnorte > 0 => numCsur == 0 /\ numP == 0
    numCsur > 0 => numCnorte == 0 /\ numP == 0
    numP > 0 => numCnorte == 0 /\ numCsur == 0 

    """
    
    def wants_enter_car(self, direction: int) -> None:
        #{INV}
        self.mutex.acquire()
        if direction ==1:
            self.VCN.wait_for(lambda: self.numCsur.value ==0 and self.numP.value ==0)
            #{INV /\ numCsur == 0 /\ numP == 0}
            self.numCnorte.value += 1
            #{INV /\ numCnorte > 0}

        else:
            self.VCS.wait_for(lambda: self.numCnorte.value ==0 and self.numP.value ==0)
            #{INV numCnorte == 0 /\ numP == 0}
            self.numCsur.value += 1
            #{INV /\ numCsur > 0}
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        #{INV /\ numC{dir} > 0} siendo dir == 0 => numC{dir}=numCsur /\ dir ==1 => numC{dir} == numCnorte
        self.mutex.acquire()
        if direction ==1: 
            #{INV /\ numCnorte > 0}
            self.numCnorte.value -= 1
            #{INV}
            self.VP.notify_all()
            self.VCS.notify_all()
        else:
            #{INV /\ numCsur > 0}
            self.numCsur.value -=1
            #{INV}
            self.VCN.notify_all()
            self.VP.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        #{INV}
        self.mutex.acquire()
        self.VP.wait_for(lambda: self.numCsur.value ==0 and self.numCnorte.value ==0)
        #{INV /\ numCsur == 0 /\ numCnorte ==0}
        self.numP.value += 1
        #{INV /\ numP > 0}
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        #{INV /\ numP > 0}
        self.mutex.acquire()
        self.numP.value -= 1
        #{INV}
        self.VCS.notify_all()
        self.VP.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return f'Monitor:\n numero coches norte pasando:{self.numCnorte.value}\n numero coches sur pasando {self.numCsur.value} \n numero peatones pasando {self.numP.value}\n -------------------------------------------\n'

def delay_car_north() -> None:
    time.sleep(max(random.normalvariate(1,.25),.1))

def delay_car_south() -> None:
    time.sleep(max(random.normalvariate(1,.25),.1))

def delay_pedestrian() -> None:
    time.sleep(random.normalvariate(5, 1))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    #{INV}
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    #{INV /\ numC{dir} > 0} siendo dir == 0 => numC{dir}=numCsur /\ dir ==1 => numC{dir} == numCnorte
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    #{INV}
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    #{INV}
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    #{INV /\ numP > 0}
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    #{INV}
    print(f"pedestrian {pid} out of the bridge. {monitor}")

def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))#Variable aleatoria exponencial negativa
    for p in plst:
        p.join()

def gen_cars(monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        direction = NORTH if random.randint(0,1)==1  else SOUTH
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_CARS))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars = Process(target=gen_cars, args=(monitor,))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars.start()
    gped.start()
    gcars.join()
    gped.join()
    print("TERMINADO")

if __name__ == '__main__':
    main()

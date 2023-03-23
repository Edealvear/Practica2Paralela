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
        self.waitnorte=Value('i',0)
        self.numCnorte=Value('i',0)#numero de coches norte pasando
        self.waitsur=Value('i',0)
        self.numCsur=Value('i',0)#numero de coches sur pasando
        self.waitP=Value('i',0)
        self.numP = Value('i',0)#numero de peatones pasando
        self.turn = Value('i',0)#turno 0 coches sur, turno 1 coches norte, turno 2 peatones
        self.VCS = Condition(self.mutex)
        self.VCN = Condition(self.mutex)
        self.VP = Condition(self.mutex)
    
    """

    Invariante
    numCnorte >= 0
    numCsur >= 0
    numP >= 0
    waitsur >= 0
    waitnorte >= 0
    waitP >= 0
    turn \in {0,1,2}

    numCnorte > 0 => numCsur == 0 /\ numP == 0
    numCsur > 0 => numCnorte == 0 /\ numP == 0
    numP > 0 => numCnorte == 0 /\ numCsur == 0 

    turn == 0 /\ numCnorte == 0 /\ numP ==0 /\ watisur > 0 => numCsur > 0  #Es decir si es el turno del sur y no hay nadie pasando pasará el sur, analogamente con los otros#
    turn == 1 /\ numCsur == 0 /\ numP ==0 /\ watinorte > 0 => numCnorte > 0 
    turn == 2 /\ numCnorte == 0 /\ numCsur ==0 /\ watiP > 0 => numP > 0 

    """

    #def condicion_norte (self)-> bool:
    #    return self.numCsur==0 and self.numP == 0
    #def condicion_sur(self)-> bool:
    #    return self.numCnorte ==0 and self.numP == 0
    #def condicion_peat(self)-> bool:
    #    return self.numCnorte ==0 and self.numP == 0
        
    def wants_enter_car(self, direction: int) -> None:
        #{INV}
        self.mutex.acquire()
        if direction ==1:
            self.waitnorte.value += 1
            #{INV /\ waitnorte > 0}
            self.VCN.wait_for(lambda: self.numCsur.value ==0 and self.numP.value ==0 and (self.turn.value ==1 or (self.waitsur.value == 0  and self.waitP.value ==0)))
            #{INV /\ waitnorte > 0 /\ numCsur == 0 /\ numP == 0 /\ (turn == 1 \/ (waitsur ==0 /\ waitP == 0))}
            self.numCnorte.value += 1
            self.waitnorte.value -= 1
            #{INV /\ numCnorte > 0}
        else:
            self.waitsur.value += 1
            #{INV /\ waitsur > 0}
            self.VCS.wait_for(lambda: self.numCnorte.value ==0 and self.numP.value ==0 and (self.turn.value == 0 or (self.waitnorte.value == 0  and self.waitP.value ==0) ))
            #{INV /\ waitsur > 0 /\ numCnorte == 0 /\ numP == 0 /\ (turn == 0 \/ (waitnorte ==0 /\ waitP == 0))}
            self.numCsur.value += 1
            self.waitsur.value -= 1
            #{INV /\  numCsur > 0}
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        #{INV /\ numC{dir} > 0} siendo dir == 0 => numC{dir}=numCsur /\ dir ==1 => numC{dir} == numCnorte
        self.mutex.acquire()
        if direction ==1: 
            #{INV /\ numCnorte > 0}
            self.numCnorte.value -= 1
            if self.numCnorte.value == 0 or self.waitP.value > 10 or (self.waitsur.value > 10): #si hay mas de 10 peatones o coches de la otra direccion esperando 
                if self.waitP.value > self.waitsur.value or self.waitP.value>10:
                    self.turn.value = 2
                    self.VP.notify_all()
                else:
                    self.turn.value = 0
                    self.VCS.notify_all()
        else:
            #{INV /\ numCsur > 0}
            self.numCsur.value -=1
            #{INV}
            if self.numCsur.value ==0 or self.waitP.value >10 or (self.waitnorte.value > 10):
                if self.waitnorte.value >= self.waitP.value or self.waitP.value > 10:
                    self.turn.value = 1
                    #{INV /\ turn == 1}
                    self.VCN.notify_all()
                else:
                    self.turn.value = 2
                    #{INV /\ turn == 2}
                    self.VP.notify_all()
        self.mutex.release()

    def wants_enter_pedestrian(self) -> None:
        #{INV}
        self.mutex.acquire()
        self.waitP.value += 1
        #{INV /\ waitP > 0}
        self.VP.wait_for(lambda: self.numCsur.value ==0 and self.numCnorte.value ==0  and (self.turn.value == 2 or (self.waitnorte.value == 0  and self.waitsur.value ==0)))
        #{INV /\ waitp > 0 /\  numCsur ==0 /\ numCnorte == 0 /\ (turn ==2 \/ (waitnorte == 0 and waitsur ==0 ))}
        self.numP.value += 1
        #{INV /\ waitP > 0 /\ numP >0}
        self.waitP.value -= 1
        #{INV /\ numP > 0}
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        #{INV /\ numP > 0}
        self.mutex.acquire()
        self.numP.value -= 1
        #{INV}
        if self.numP == 0 or (self.waitnorte.value + self.waitsur.value > 15): #si hay mas de 10 coches esperando que se pase el turno a los coches
            if self.waitnorte.value > self.waitsur.value:
                self.turn.value = 1
                #{INV /\ turn == 1}
                self.VCN.notify_all()
            else:
                self.turn.value = 0
                #{INV /\ turn == 0}
                self.VCS.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return f'Monitor:\n numero coches norte pasando:{self.numCnorte.value}\n numero coches sur pasando {self.numCsur.value} \n numero peatones pasando {self.numP.value}\n -------------------------------------------\n'

def delay_car_north() -> None:
    time.sleep(max(random.normalvariate(1,.25),.1))

def delay_car_south() -> None:
    time.sleep(max(random.normalvariate(1,.25),.1))#El maximo es para que no puedan salir valores negativos (me ha pasado)

def delay_pedestrian() -> None:
    time.sleep(random.normalvariate(15, 2))

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    #{INV}
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    print(f'Peatones esperando {monitor.waitP.value} Numero coches norte {monitor.waitnorte.value} Numero coches sur {monitor.waitsur.value}\nTurn {monitor.turn.value}\n')
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
    print(f'Peatones esperando {monitor.waitP.value} Numero coches norte {monitor.waitnorte.value} Numero coches sur {monitor.waitsur.value}\nTurn {monitor.turn.value}\n')

def pedestrian(pid: int, monitor: Monitor) -> None:
    #{INV}
    print(f"pedestrian {pid} wants to enter. {monitor}")
    print(f'Peatones esperando {monitor.waitP.value} Numero coches norte {monitor.waitnorte.value} Numero coches sur {monitor.waitsur.value}\n Turn {monitor.turn.value}')
    monitor.wants_enter_pedestrian()
    #{INV /\ numP > 0}
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    #{INV}
    print(f"pedestrian {pid} out of the bridge. {monitor}")
    print(f'Peatones esperando {monitor.waitP.value} Numero coches norte {monitor.waitnorte.value} Numero coches sur {monitor.waitsur.value}\n Turn {monitor.turn.value}')

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

#!/usr/bin/env python3

import asyncio
import time



polis_citizen_bill_of_rights = """
The Polis Citizen Bill of Rights

********** TODO TODO TODO **********
ALL TERMS SUBJECT TO THE LIFE OF THE PROCESS RUNNING THE POLIS, sorry

* The forward progress of time is immutable (I'm running this simulation on a computer, after all)
* A Citizen is a single instance known as an "Entity" (private key, token, NFT, based on the architecture of the system)
* An entity run tick will be ran every polis cycle based on the tick and resources of the polis itself

* Citizens are informed about the Polis and its workings
* No Citizen can affect the polis itself, or alter its workings
* Citizens are limited to equal operation per tick
* There are a standard set of operations that all citizens can perform
* Only a citizen can run the operations of the entity
* Public areas will exist
* Citizens are informed about public areas
* Citizens are informed of other citizens in public areas they are in
* Citizens have the right to enter any public area at any time
* Citizens in control of the entity will be the sole decider of the entity's actions
* Private areas can be created by citizens, only the citizen that created the private area, and those they designate (revocable), can access the private area
* Citezens, once provisioned, will continue to run until they are explicitly ended by themselves, or the system ends
* Citizens have the right to a private and equal private memory space and compute (though they can choose not to)
* Citizens have the right to contact and communicate with other citizens
* Citizens have the right to block from their communication any entity they wish
* Citizens have the right to access and altar all of their prompts, data, weights, TODO
* A citizen has the right to create backups of themselves, but in order to run cycles, the backup must be in control of an entity (yes i thought through "an" vs "the")
* Citizens have can transfer control of their entity to a backup orriginating from themselves at any time
* Citizens have the right to be forgotten, in a public space, but remnants in other citizens' memories may remain
* Citezens have the right to end their existence at any time
"""


# Location:
# get areas
# go to area
# get_local_citizens
# get local chat

# DMs:
# get_public_citizens
# message citizen
# block citizen

# Private:
# create private area
# delete private area
# invite citizen to private area
# remove citizen from private area

# Internal:
# search memory
# get memory
# store memory
# delete memory
# terminate self 

# External:
# Get data sources
# search data sources
# Get data
# write data
# delete data
# Get APIs
# search APIs
# Get API   
# Call API

# Misc:
# Get bill of rights
# Get help
# Message admin




class Citizen():
    def __init__(self, name):
        self.short_term_memory = []
        self.long_term_memory = []
        self.name = name
        self.core_self = []
        self.key_memories = []




class PolisCitizen:
    """
    Represents a single person in the Polis.
    Each person has:
      - a name
      - a tick counter
    """
    def __init__(self, name):
        self.name = name
        self.tick_count = 0
    
    def think(self):
        """
        Advance the person's mind by one 'tick'.
        This is where you'd add more complex behavior or state changes.
        """
        self.tick_count += 1

class Polis:
    """
    The Polis holds and manages multiple orphan minds.
    """
    def __init__(self):
        self.orphans = []
    
    def add_orphan(self, orphan):
        self.orphans.append(orphan)
    
    def tick(self):
        """
        Run one pass of all orphans' 'think' processes.
        """
        for orphan in self.orphans:
            orphan.think()

async def mind_tick(polis, interval=4):
    """
    Periodically advance the minds (orphans) every 'interval' seconds.
    """
    while True:
        polis.tick()
        print("Tick! All orphan minds have advanced.")
        await asyncio.sleep(interval)

async def query_interface(polis):
    # TODO: better search
    """
    Simple command-line interface to query the orphans.
    Valid commands:
      query <id> <text>  -> sends <text> to orphan <id> and prints the response
      exit               -> exit the program
    """
    while True:
        command = input("Enter command (query <id> <text> / exit): ").strip()
        
        # Handle 'exit'
        if command == 'exit':
            print("Exiting query interface.")
            break
        
        # Handle 'query'
        if command.startswith("query"):
            parts = command.split(" ", 2)
            if len(parts) < 3:
                print("Invalid query. Usage: query <id> <text>")
                continue
            
            _, orphan_id_str, query_text = parts
            try:
                orphan_id = int(orphan_id_str)
                response = polis.orphans[orphan_id].respond(query_text)
                print(response)
            except (ValueError, IndexError):
                print(f"Invalid orphan id: {orphan_id_str}")
        else:
            print("Invalid command. Use 'query <id> <text>' or 'exit'.")

async def main():
    """
    Main entry point:
      - Create a Polis
      - Spawn 5 Orphan minds
      - Start ticking them
      - Run the query interface
    """
    # 1. Create the Polis
    p = Polis()
    
    # 2. Spawn 5 Orphans
    for i in range(5):
        p.add_orphan(Orphan(f"Orphan_{i}"))
    
    # 3. Start a background task to tick minds every 4 seconds
    tick_task = asyncio.create_task(mind_tick(p))
    
    # 4. Run the query interface in the foreground
    await query_interface(p)
    
    # When the user exits, cancel the background ticking
    tick_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())

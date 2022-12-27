import csv
import os
import sys
import optparse
from random import randint
from sumolib import checkBinary
import traci

# VERIFY THAT SUMO IS INSTALLED AND PATH IS SET UP
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
else:
    sys.exit("ERROR: Please declare SUMO_HOME in your environment variables.")

# GET OPTIONS
def get_options():
    opt_parser = optparse.OptionParser()
    opt_parser.add_option("--nogui", action="store_true", default=False, help="run the commandline version of SUMO")
    options, args = opt_parser.parse_args()
    return options

# RETURNS TRUE IF THERE IS AN ACTIVE BLUE LIGHT DEVICE IN VEH_ID_LIST
def isEMSPresent(veh_id_list):
    for vehID in veh_id_list:
            if traci.vehicle.getParameterWithKey(vehID, "has.bluelight.device")[1] == 'true':
                return True
    return False

# BASE TRACI CONTROL LOOP
def run():
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # DO TRACI THINGS HERE
        step += 1
    traci.close()
    sys.stdout.flush()
    pass


def run_reaction_simulation(bluelight_reaction_time=25.0):

    EMS_is_present = False
    ems_time_present_step_count = 0
    ems_id = ''
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        # Get list of vehicle IDs
        veh_id_list = traci.vehicle.getIDList()
        # If EMS vehicle is present
        if EMS_is_present:
            # print("Waiting for EMS to leave again...")
            ems_time_present_step_count += 1
            # Check if it left this step
            if (isEMSPresent(veh_id_list)) == False:
                # print("EMS just left... time present =", ems_time_present_step_count)
                EMS_is_present = False
                break
        # Else if EMS vehicle is NOT present
        else:
            # If it arrived this step
            if isEMSPresent(veh_id_list):
                # print("EMS just appeared... set reaction_assignment_break to true... assigning reaction distances")
                EMS_is_present = True
                # Store ems_id to use for reactiondist setter
                for veh in veh_id_list:
                    if traci.vehicle.getParameterWithKey(veh, "has.bluelight.device")[1] == 'true':
                        ems_id = veh
                # Set reactiondist
                traci.vehicle.setParameter(ems_id, "device.bluelight.reactiondist", bluelight_reaction_time)
            # else:
                # print("Waiting on EMS to appear...")
        traci.simulationStep()
        step += 1
    # ----------------------------------
    traci.close()
    sys.stdout.flush()
    return ems_time_present_step_count

def perform_reaction_time_experiment(min_reaction_time=0, max_reaction_time=25, increment=1):

    results_file = open('results.csv', 'w', newline='')
    writer = csv.writer(results_file)

    x = []
    y = []

    max_reaction_time = max_reaction_time
    for i in range(min_reaction_time, max_reaction_time, increment):
        
        # TraCI starts sumo as a subprocess and then this script connects and runs
        traci.start(["sumo", "-c", FILENAME])
        time = run_reaction_simulation(bluelight_reaction_time=float(i))
        x.append(i)
        y.append(time)
        result_tuple = (i, time)
        writer.writerow(result_tuple)
        print("Reaction test for i =", i , "complete...", (i/max_reaction_time) * 100, "%")

    import matplotlib.pyplot as plt

    plt.style.use('fivethirtyeight')

    plt.scatter(x, y)
    plt.tight_layout()
    plt.xlabel('Reaction Time')
    plt.ylabel('EMS Travel Time')
    plt.title('Impact of Reaction Time on EMS Travel Time')
    plt.savefig("results.jpg", bbox_inches='tight')
    plt.show()
    plt.close('all')


# Main
if __name__ == "__main__":
    options = get_options()
    FILENAME = "simulation.sumocfg"

    # check binary
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else: sumoBinary = checkBinary('sumo-gui')

    cmd =   [   sumoBinary,
                "-c",
                FILENAME,
                "--tripinfo-output",
                "tripinfo.xml"
            ]

    perform_reaction_time_experiment(10, 15, 1)
    

    

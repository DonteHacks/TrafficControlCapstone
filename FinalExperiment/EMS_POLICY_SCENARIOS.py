import os
import sys
import optparse
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

# Returns whether or not an EMS vehicle is present in the simulation
def isEMSPresent(veh_id_list):
    for vehID in veh_id_list:
            if traci.vehicle.getParameterWithKey(vehID, "has.bluelight.device")[1] == 'true':
                return True
    return False

# SET A PARTICULAR INTERSECTION TO A SPECIFIED EMS POLICY
def ems_policy(ems_policy, intersection_id):
    # Green Corridor (Turn EMS lanes for intersection green)
    if ems_policy == 'gc':
        traci.trafficlight.setRedYellowGreenState(intersection_id, 'GGGGrrrrGGGGrrrr')
        return
    # Red Freeze (Turn all lights for intersection red)
    elif ems_policy == 'rf':
        traci.trafficlight.setRedYellowGreenState(intersection_id, 'rrrrrrrrrrrrrrrr')
        return
    # Normal policy (No traffic light manipulation)
    elif ems_policy == 'na':
        # DO NOTHING HERE
        pass
    else:
        raise Exception("You did not enter a valid EMS-policy type. Please re-run with one of the following options:\n\n<gc (green corridor) | rf (red freeze) | na (normal lights)>")
    
# Define traffic light phases respective to the intersection
intersection_J3_phases = []
intersection_J3_phases.append(traci.trafficlight.Phase(42, "rrrrGGGgrrrrGGGg", 0, 0))
intersection_J3_phases.append(traci.trafficlight.Phase(3, "rrrryyyyrrrryyyy", 0, 0))
intersection_J3_phases.append(traci.trafficlight.Phase(42, "GGGgrrrrGGGgrrrr", 0, 0))
intersection_J3_phases.append(traci.trafficlight.Phase(3, "yyyyrrrryyyyrrrr", 0, 0))

intersection_J4_phases = []
intersection_J4_phases.append(traci.trafficlight.Phase(36, "rrrrGGGgrrrrGGGg", 0, 0))
intersection_J4_phases.append(traci.trafficlight.Phase(6, "rrrryyyGrrrryyyG", 0, 0))
intersection_J4_phases.append(traci.trafficlight.Phase(3, "rrrrrrryrrrrrrry", 0, 0))
intersection_J4_phases.append(traci.trafficlight.Phase(36, "GGGgrrrrGGGgrrrr", 0, 0))
intersection_J4_phases.append(traci.trafficlight.Phase(6, "yyyGrrrryyyGrrrr", 0, 0))
intersection_J4_phases.append(traci.trafficlight.Phase(3, "rrryrrrrrrryrrrr", 0, 0))

intersection_J5_phases = []
intersection_J5_phases.append(traci.trafficlight.Phase(42, "GGGgrrrrGGGgrrrr", 0, 0))
intersection_J5_phases.append(traci.trafficlight.Phase(3, "yyyyrrrryyyyrrrr", 0, 0))
intersection_J5_phases.append(traci.trafficlight.Phase(42, "rrrrGGGgrrrrGGGg", 0, 0))
intersection_J5_phases.append(traci.trafficlight.Phase(3, "rrrryyyyrrrryyyy", 0, 0))

# Map intersection name to phase list, so we can easily reference them with strings
int_to_phases_map = {   'J3' : intersection_J3_phases,
                        'J4' : intersection_J4_phases,
                        'J5' : intersection_J5_phases   }

# This method returns a particular intersection back to it's normal traffic light phases
# after it has had an EMS policy suddenly change it's pattern
def return_to_normal(intersection_id):
    logic = traci.trafficlight.Logic("custom", 0, 0, int_to_phases_map[intersection_id])
    traci.trafficlight.setCompleteRedYellowGreenDefinition(intersection_id, logic)
    traci.trafficlight.setPhase(intersection_id, 0)

# BASE TRACI CONTROL LOOP
def run(sumo_gui, FILENAME, policy_type):

    # Start traci
    traci.start([sumo_gui, "-c", FILENAME])
    step = 0

    # Declare freeze_break
    freeze_break = 0

    # Set freeze_break for gridlocked traffic
    # If traffic gets weird, SUMO-typical gridlock, if we pass the freeze break values below,
    # We know we have to rerun the simulation
    if "LIGHT" in FILENAME:
        print("FREEEEEEEEEEEEEEEZE BREAK = 250")
        freeze_break = 250
    elif "MEDIUM" in FILENAME:
        print("FREEEEEEEEEEEEEEEZE BREAK = 400")
        freeze_break = 400
    elif "HEAVY" in FILENAME:
        print("FREEEEEEEEEEEEEEEZE BREAK = 750")
        freeze_break = 750
    else:
        raise Exception("Should never hit...")

    # Declaration of detector booleans
    det1_FAR    = False
    det1_NEAR   = False
    det2_FAR    = False
    det2_NEAR   = False
    det3_FAR    = False
    det3_NEAR   = False
    det4_FAR    = False
    det4_NEAR   = False

    # Boolean for whether or not the EMS vehicle has finished its route
    finished = False

    # Booleans for keeping track of whether or not the middle intersections have already been normalized.
    J3_normaled = False
    J4_normaled = False

    count_EMS_time_steps = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # If EMS is present, increment the step counter for measuring it's travel time... count_EMS_time_steps
        if(isEMSPresent(traci.vehicle.getIDList())):
            count_EMS_time_steps += 1
        # SET DETECTOR BOOLEANS FOR THE CURRENT STEP, SO WE KNOW WHERE THE EMS VEHICLE IS ON THE ROAD
        if not det1_FAR:
            det1_FAR    = traci.multientryexit.getLastStepVehicleNumber('det1_FAR')
        if not det1_NEAR:
            det1_NEAR   = traci.multientryexit.getLastStepVehicleNumber('det1_NEAR')
        if not det2_FAR:
            det2_FAR    = traci.multientryexit.getLastStepVehicleNumber('det2_FAR')
        if not det2_NEAR:
            det2_NEAR   = traci.multientryexit.getLastStepVehicleNumber('det2_NEAR')
        if not det3_FAR:
            det3_FAR    = traci.multientryexit.getLastStepVehicleNumber('det3_FAR')
        if not det3_NEAR:
            det3_NEAR   = traci.multientryexit.getLastStepVehicleNumber('det3_NEAR')
        if not det4_FAR:
            det4_FAR    = traci.multientryexit.getLastStepVehicleNumber('det4_FAR')
        if not det4_NEAR:
            det4_NEAR   = traci.multientryexit.getLastStepVehicleNumber('det4_NEAR')
        # GREEN CORRIDOR POLICY IMPLEMENTATION
        if policy_type == 'gc':
            if not finished:
                if det1_FAR and not det2_FAR:
                    ems_policy(policy_type, 'J3')
                    ems_policy(policy_type, 'J4')
                    ems_policy(policy_type, 'J5')
                elif det2_FAR and not det3_FAR:
                    if not J3_normaled:
                        return_to_normal('J3')
                        J3_normaled = True
                elif det3_FAR and not det4_FAR:
                    if not J4_normaled:
                        return_to_normal('J4')
                        J4_normaled = True
                elif det4_FAR:
                    return_to_normal('J5')
                    finished = True
        # RED FREEZE POLICY IMPLEMENTATION
        elif policy_type == 'rf':
            if not finished:
                if det1_NEAR and not det2_FAR:
                    ems_policy(policy_type, 'J3')
                elif det2_FAR and not det2_NEAR:
                    if not J3_normaled:
                        return_to_normal('J3')
                        J3_normaled = True
                elif det2_NEAR and not det3_FAR:
                    ems_policy(policy_type, 'J4')
                elif det3_FAR and not det3_NEAR:
                    if not J4_normaled:
                        return_to_normal('J4')
                        J4_normaled = True
                elif det3_NEAR and not det4_FAR:
                    ems_policy(policy_type, 'J5')
                elif det4_FAR:
                    return_to_normal('J5')
                    finished = True
        elif policy_type == 'na':
            pass
        else:
            raise Exception("{} is not a valid policy...".format(policy_type))
        # Increments simulation steps
        step+=1
        # Attempts to redo gridlocked simulations
        if step > freeze_break:
            # Print BREAKING, as well as how many vehicles were left in the simulation
            print('////BREAKING//// {}'.format(traci.vehicle.getIDCount()))
            # Close traci and flush output
            traci.close()
            sys.stdout.flush()
            # Rerun the simulation
            count_EMS_time_steps, step = run(sumo_gui, FILENAME, policy_type)
            # Return the rerun-simulation results
            return count_EMS_time_steps, step
    traci.close()
    sys.stdout.flush()

    # Attempts to redo gridlocked simulations
    if step > freeze_break:
        # Print BREAKING, as well as how many vehicles were left in the simulation
        print('////BREAKING//// {}'.format(traci.vehicle.getIDCount()))
        # Rerun the simulation
        count_EMS_time_steps, step = run(sumo_gui, FILENAME, policy_type)
        # Return the rerun-simulation results
        return count_EMS_time_steps, step
    else:
        # Return the rerun-simulation results
        return count_EMS_time_steps, step

def run_all_policies_experiment(sumo_gui, FILENAMES):

    # Define iterations
    iterations = 10

    # Define calculation variables
    light_gc_ems_total = 0
    light_gc_cong_total = 0
    light_rf_ems_total = 0
    light_rf_cong_total = 0
    light_na_ems_total = 0
    light_na_cong_total = 0
    average_gc_ems_total = 0
    average_gc_cong_total = 0
    average_rf_ems_total = 0
    average_rf_cong_total = 0
    average_na_ems_total = 0
    average_na_cong_total = 0
    heavy_gc_ems_total = 0
    heavy_gc_cong_total = 0
    heavy_rf_ems_total = 0
    heavy_rf_cong_total = 0
    heavy_na_ems_total = 0
    heavy_na_cong_total = 0

    # Run "iteration" amount of simulations on FILENAME[0] to get sum for average calculation below
    for i in range(iterations):
        print('Running GREEN CORRIDOR policy...')
        light_gc_ems_steps, light_gc_cong_steps = run(sumo_gui, FILENAMES[0], 'gc')
        light_gc_ems_total += light_gc_ems_steps
        light_gc_cong_total += light_gc_cong_steps
        print('Running RED FREEZE policy...')
        light_rf_ems_steps, light_rf_cong_steps = run(sumo_gui, FILENAMES[0], 'rf')
        light_rf_ems_total += light_rf_ems_steps
        light_rf_cong_total += light_rf_cong_steps
        print('Running NORMAL policy (no traffic light manipulation)...')
        light_na_ems_steps, light_na_cong_steps = run(sumo_gui, FILENAMES[0], 'na')
        light_na_ems_total += light_na_ems_steps
        light_na_cong_total += light_na_cong_steps

    # Run "iteration" amount of simulations on FILENAME[1] to get sum for average calculation below
    for i in range(iterations):
        print('Running GREEN CORRIDOR policy...')
        average_gc_ems_steps, average_gc_cong_steps = run(sumo_gui, FILENAMES[1], 'gc')
        average_gc_ems_total += average_gc_ems_steps
        average_gc_cong_total += average_gc_cong_steps
        print('Running RED FREEZE policy...')
        average_rf_ems_steps, average_rf_cong_steps = run(sumo_gui, FILENAMES[1], 'rf')
        average_rf_ems_total += average_rf_ems_steps
        average_rf_cong_total += average_rf_cong_steps
        print('Running NORMAL policy (no traffic average manipulation)...')
        average_na_ems_steps, average_na_cong_steps = run(sumo_gui, FILENAMES[1], 'na')
        average_na_ems_total += average_na_ems_steps
        average_na_cong_total += average_na_cong_steps

    # Run "iteration" amount of simulations on FILENAME[2] to get sum for average calculation below
    for i in range(iterations):
        print('Running GREEN CORRIDOR policy...')
        heavy_gc_ems_steps, heavy_gc_cong_steps = run(sumo_gui, FILENAMES[2], 'gc')
        heavy_gc_ems_total += heavy_gc_ems_steps
        heavy_gc_cong_total += heavy_gc_cong_steps
        print('Running RED FREEZE policy...')
        heavy_rf_ems_steps, heavy_rf_cong_steps = run(sumo_gui, FILENAMES[2], 'rf')
        heavy_rf_ems_total += heavy_rf_ems_steps
        heavy_rf_cong_total += heavy_rf_cong_steps
        print('Running NORMAL policy (no traffic light manipulation)...')
        heavy_na_ems_steps, heavy_na_cong_steps = run(sumo_gui, FILENAMES[2], 'na')
        heavy_na_ems_total += heavy_na_ems_steps
        heavy_na_cong_total += heavy_na_cong_steps

    # --- BEGIN AVERAGE CALCULATIONS --- 
    light_gc_ems_average    = (int) (light_gc_ems_total / iterations)
    light_rf_ems_average    = (int) (light_rf_ems_total / iterations)
    light_na_ems_average    = (int) (light_na_ems_total / iterations)

    light_gc_cong_average   = (int) (light_gc_cong_total / iterations)
    light_rf_cong_average   = (int) (light_rf_cong_total / iterations)
    light_na_cong_average   = (int) (light_na_cong_total / iterations)

    average_gc_ems_average  = (int) (average_gc_ems_total / iterations)
    average_rf_ems_average  = (int) (average_rf_ems_total / iterations)
    average_na_ems_average  = (int) (average_na_ems_total / iterations)

    average_gc_cong_average = (int) (average_gc_cong_total / iterations)
    average_rf_cong_average = (int) (average_rf_cong_total / iterations)
    average_na_cong_average = (int) (average_na_cong_total / iterations)

    heavy_gc_ems_average    = (int) (heavy_gc_ems_total / iterations)
    heavy_rf_ems_average    = (int) (heavy_rf_ems_total / iterations)
    heavy_na_ems_average    = (int) (heavy_na_ems_total / iterations)

    heavy_gc_cong_average   = (int) (heavy_gc_cong_total / iterations)
    heavy_rf_cong_average   = (int) (heavy_rf_cong_total / iterations)
    heavy_na_cong_average   = (int) (heavy_na_cong_total / iterations)
    # --- END AVERAGE CALCULATIONS --- 

    print('\n\n---------------- AVERAGE RESULTS ----------------\n')
    print('{}:\n'.format(FILENAMES[0]))
    print('\tGREEN CORRIDOR:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(light_gc_ems_average, light_gc_cong_average))
    print('\tRED FREEZE:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(light_rf_ems_average, light_rf_cong_average))
    print('\tCONTROL (no traffic light manipulation):\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(light_na_ems_average, light_na_cong_average))

    print('{}:\n'.format(FILENAMES[1]))
    print('\tGREEN CORRIDOR:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(average_gc_ems_average, average_gc_cong_average))
    print('\tRED FREEZE:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(average_rf_ems_average, average_rf_cong_average))
    print('\tCONTROL (no traffic light manipulation):\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(average_na_ems_average, average_na_cong_average))

    print('{}:\n'.format(FILENAMES[2]))
    print('\tGREEN CORRIDOR:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(heavy_gc_ems_average, heavy_gc_cong_average))
    print('\tRED FREEZE:\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(heavy_rf_ems_average, heavy_rf_cong_average))
    print('\tCONTROL (no traffic light manipulation):\n\t\tEMS travel time = {} steps\n\t\tCongestion clearing time = {} steps\n'.format(heavy_na_ems_average, heavy_na_cong_average))
    print('-----------------------------------------\n')

# MAIN
if __name__ == "__main__":

    options = get_options()

    # Define the filenames for the sumoconfigs we want to run simulations on
    FILENAMES = ["simulation_LIGHT.sumocfg", 
                 "simulation_MEDIUM.sumocfg", 
                 "simulation_HEAVY.sumocfg"]

    # Determine whether or not to run sumo with the GUI or without
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else: sumoBinary = checkBinary('sumo-gui')

    # Ask user if they want to use the SUMO GUI, and assign
    # appropriate value to sumo_gui
    user_input = input("\nRun with GUI? [Y/N]\n\n")

    if user_input.lower() == 'y':
        sumo_gui = 'sumo-gui'
    else:
        sumo_gui = 'sumo'

    # Run experiment
    run_all_policies_experiment(sumo_gui, FILENAMES)
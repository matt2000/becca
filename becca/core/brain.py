"""
The Brain class.
"""

from __future__ import print_function
import cPickle as pickle
import os
import numpy as np

from becca.core.affect import Affect
from becca.core.level import Level

# Identify the full local path of the brain.py module.
# This trick is used to conveniently locate other BECCA resources.
MODPATH = os.path.dirname(os.path.abspath(__file__))

class Brain(object):
    """
    A biologically motivated learning algorithm.

    Attributes
    ----------
    affect : Affect
        See the pydocs in the module ``affect.py`` for the class ``Affect``.
    backup_interval : int
        The number of time steps between saving a copy of the ``brain``
        out to a pickle file for easy recovery.
    levels : list of ``Level``
        Collectively, the levels form a hierarchy with ``levels[0]``
        on the bottom.
        Refer to ``level.py`` for a detailed description of a level.
    log_dir : str
        Relative path to the ``log`` directory. This is where backups
        and images of the ``brain``'s state and performance are kept.
    name : str
        Unique name for this ``brain``.
    num_actions : int
        The number of distinct actions that the ``brain`` can choose to
        execute in the world.
    num_features : int
        The total number of features, including sensors and all features
        derived from them.
    num_sensors : int
        The number of distinct sensors that the world will be passing in
        to the ``brain``.
    pickle_filename : str
        Relative path and filename of the backup pickle file.
    satisfaction : float
        The level of contentment experienced by the brain. Higher contentment
        dampens curiosity and the drive to explore.
    timestep : int
        The age of the ``brain`` in discrete time steps.
    """


    def __init__(self, num_sensors, num_actions, brain_name='test_brain'):
        """
        Configure the Brain.

        Parameters
        ----------
        """
        self.num_sensors = num_sensors
        # Always include an extra action. The last is the 'do nothing' action.
        self.num_actions = num_actions + 1

        self.backup_interval = 1e5
        self.name = brain_name
        self.log_dir = os.path.normpath(os.path.join(MODPATH, '..', 'log'))
        if not os.path.isdir(self.log_dir):
            os.makedirs(self.log_dir)
        self.pickle_filename = os.path.join(self.log_dir,
                                            '{0}.pickle'.format(brain_name))
        self.affect = Affect()
        self.satisfaction = 0.

        # Initialize the first ``Level``
        num_elements = self.num_sensors + self.num_actions
        num_sequences = 3 * num_elements
        level_index = 0
        level_0 = Level(level_index, num_elements, num_sequences)
        self.levels = [level_0]
        self.actions = np.zeros(self.num_actions)

        self.timestep = 0


    def sense_act_learn(self, sensors, reward):
        """
        Take sensor and reward data in and use them to choose an action.

        Parameters
        ----------
        sensors : array of floats
            The information coming from the sensors in the world.
            The array should have ``self.num_sensors`` elements.
            Each value in the array is expected to be between 0 and 1,
            inclusive. Sensor values are interpreted as fuzzy binary
            values, rather than continuous values. For instance,
            the ``brain`` doesn't interpret a contact sensor value of .5
            to mean that the contact
            sensor was only weakly contacted. It interprets it
            to mean that the sensor was fully contacted for 50% of the sensing
            duration or that there is a 50% chance that the sensor was
            fully contacted during the entire sensing duration. For another
            example, a light sensor reading of zero won't be
            interpreted as by the ``brain`` as darkness. It will just be
            interpreted as a lack of information about the lightness.
        reward : float
            The extent to which the ``brain`` is being rewarded by the
            world. It is expected to be between -1 and 1, inclusive.
            -1 is the worst pain ever. 1 is the most intense ecstasy
            imaginable. 0 is neutral.

        Returns
        -------
        actions : array of floats
            The action commands that the ``brain`` is sending to the world
            to be executed. The array should have ``self.num_actions``
            elements in it. Each value should be binary: 0 and 1. This
            allows the ``brain`` to learn most effectively how to interact
            with the world to obtain more reward.
        """
        self.timestep += 1

        # Calculate the "mood" of the agent.
        self.satisfaction = self.affect.update(reward)

        # Calcuate activities of all the sequences in the hierarchy.
        element_activities = np.concatenate((sensors, self.actions))
        for level in self.levels:
            #sequences = level.update_elements(elements)
            sequence_activities = level.step(element_activities,
                                             reward,
                                             self.satisfaction)

            # For the next level
            element_activities = sequence_activities

        # Pass goals back down.
        for i in range(len(self.levels) - 1)[::-1]:
            self.levels[i].sequence_goals = self.levels[i + 1].element_goals

        # Decide which actions to take.
        self.actions = self.levels[0].element_goals
        print('self.actions' + str(self.actions))
        # debug: Random actions
        # self.actions = self.random_actions()

        # Update level 0 with selected ``actions``.
        #start_index = self.num_sensors
        #self.levels[0].update_elements(self.actions, start_index)

        # Periodically back up the ``brain``.
        if (self.timestep % self.backup_interval) == 0:
            self.backup()

        # Account for the fact that the last "do nothing" action
        # was added by the ``brain``.
        return self.actions[:-1]


    def random_actions(self):
        """
        Generate a random set of actions.

        Returns
        -------
        actions : array of floats
            See ``sense_act_learn.actions``.
        """
        threshold = 1. / float(self.num_actions)
        action_strength = np.random.random_sample(self.num_actions)
        actions = np.zeros(self.num_actions)
        actions[np.where(action_strength < threshold)] = 1.
        return actions


    def report_performance(self):
        """
        Make a report of how the brain did over its lifetime.

        Returns
        -------
        performance : float
            The average reward per time step collected by
            the ``brain`` over its lifetime.
        """
        return self.affect.visualize(self.timestep, self.name, self.log_dir)


    def backup(self):
        """
        Archive a copy of the brain object for future use.

        Returns
        -------
        success : bool
            If the backup process completed without any problems, ``success``
            is True, otherwise it is False.
        """
        success = False
        try:
            with open(self.pickle_filename, 'wb') as brain_data:
                pickle.dump(self, brain_data)
            # Save a second copy. If you only save one, and the user
            # happens to ^C out of the program while it is being saved,
            # the file becomes corrupted, and all the learning that the
            # ``brain`` did is lost.
            with open('{0}.bak'.format(self.pickle_filename),
                      'wb') as brain_data_bak:
                pickle.dump(self, brain_data_bak)
        except IOError as err:
            print('File error: {0} encountered while saving brain data'.
                  format(err))
        except pickle.PickleError as perr:
            print('Pickling error: {0} encountered while saving brain data'.
                  format(perr))
        else:
            success = True
        return success


    def restore(self):
        """
        Reconstitute the brain from a previously saved brain.

        Returns
        -------
        restored_brain : Brain
            If restoration was successful, the saved ``brain`` is returned.
            Otherwise a notification prints and a new ``brain`` is returned.
        """
        restored_brain = self
        try:
            with open(self.pickle_filename, 'rb') as brain_data:
                loaded_brain = pickle.load(brain_data)

            # Compare the number of channels in the restored brain with
            # those in the already initialized brain. If it matches,
            # accept the brain. If it doesn't,
            # print a message, and keep the just-initialized brain.
            # Sometimes the pickle file is corrputed. When this is the case
            # you can manually overwrite it by removing the .bak from the
            # .pickle.bak file. Then you can restore from the backup pickle.
            if ((loaded_brain.num_sensors == self.num_sensors) and
                    (loaded_brain.num_actions == self.num_actions)):
                print('Brain restored at timestep {0} from {1}'.format(
                    str(loaded_brain.timestep), self.pickle_filename))
                restored_brain = loaded_brain
            else:
                print('The brain {0} does not have the same number'.format(
                    self.pickle_filename))
                print('of input and output elements as the world.')
                print('Creating a new brain from scratch.')
        except IOError:
            print('Couldn\'t open {0} for loading'.format(
                self.pickle_filename))
        except pickle.PickleError, err:
            print('Error unpickling world: {0}'.format(err))
        return restored_brain


    def visualize(self):
        """
        Show the current state and some history of the brain.

        This is typically called from a world's ``visualize`` method.
        """
        print(' ')
        print('{0} is {1} time steps old'.format(self.name, self.timestep))

        self.affect.visualize(self.timestep, self.name, self.log_dir)
        for level in self.levels:
            level.visualize()
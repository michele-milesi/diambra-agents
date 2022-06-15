import sys, os
import diambraArena
from wrappers.addObsWrap import AdditionalObsToChannel

from stable_baselines import logger
from stable_baselines.bench import Monitor
from stable_baselines.common.misc_util import set_global_seeds
from stable_baselines.common.vec_env import DummyVecEnv, SubprocVecEnv, VecFrameStack

def makeStableBaselinesILEnv(envPrefix, settings, seed, keyToAdd=None,
                             startIndex=0, allowEarlyResets=True, startMethod=None,
                             noVec=False, useSubprocess=False):
    """
    Create a wrapped, monitored VecEnv.
    :param settings: (dict) settings for DIAMBRA IL environment
    :param seed: (int) initial seed for RNG
    :param keyToAdd: (list) ordered parameters for environment stable baselines converter wraping function
    :param startIndex: (int) start rank index
    :param allowEarlyResets: (bool) allows early reset of the environment
    :param startMethod: (str) method used to start the subprocesses.
        See SubprocVecEnv doc for more information
    :param useSubprocess: (bool) Whether to use `SubprocVecEnv` or `DummyVecEnv` when
    :param noVec: (bool) Whether to avoid usage of Vectorized Env or not. Default: False
    :return: (VecEnv) The diambra environment
    """

    hardCore = False
    if "hardCore" in settings:
        hardCore = settings["hardCore"]

    def makeSbEnv(rank):
        def thunk():
            envId = envPrefix + str(rank)
            if hardCore:
                env = diambraImitationLearningHardCore(**settings, rank=rank)
            else:
                env = diambraImitationLearning(**settings, rank=rank)
                env = AdditionalObsToChannel(env, keyToAdd, imitationLearning=True)
            env = Monitor(env, logger.get_dir() and os.path.join(logger.get_dir(), str(rank)),
                          allow_early_resets=allowEarlyResets)
            return env
        return thunk
    set_global_seeds(seed)

    # If not wanting vectorized envs
    if noVec and settings["totalCpus"] == 1:
        return makeSbEnv(0)()

    # When using one environment, no need to start subprocesses
    if settings["totalCpus"] == 1 or not useSubprocess:
        return DummyVecEnv([makeSbEnv(i + startIndex) for i in range(settings["totalCpus"])])

    return SubprocVecEnv([makeSbEnv(i + startIndex) for i in range(settings["totalCpus"])],
                         start_method=startMethod)
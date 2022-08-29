import sys
import os
import time
import argparse
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_path, '../'))
from make_stable_baselines_env import make_stable_baselines_env
from sb_utils import linear_schedule, AutoSave, model_cfg_save
from custom_policies.custom_cnn_policy import CustCnnPolicy, local_nature_cnn_small
from custom_rl_algo.ppo2_selfplay import PPO2Selfplay

if __name__ == '__main__':
    time_dep_seed = int((time.time()-int(time.time()-0.5))*1000)

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--gameId', type=str, default="doapp", help='Game ID')
        opt = parser.parse_args()
        print(opt)

        model_folder = os.path.join(base_path, "{}StableBaselinesIntegratedSelfPlayTestModel/".format(opt.gameId))

        os.makedirs(model_folder, exist_ok=True)

        # Settings
        settings = {}
        settings["game_id"] = opt.gameId
        settings["step_ratio"] = 6
        settings["frame_shape"] = [128, 128, 1]
        settings["player"] = "P1P2"  # 2P game

        settings["characters"] = [["Random", "Random", "Random"], ["Random", "Random", "Random"]]
        settings["char_outfits"] = [2, 2]

        settings["action_space"] = ["discrete", "discrete"]
        settings["attack_but_combination"] = [True, True]

        # Wrappers settings
        wrappers_settings = {}
        wrappers_settings["no_op_max"] = 0
        wrappers_settings["reward_normalization"] = True
        wrappers_settings["clip_rewards"] = False
        wrappers_settings["frame_stack"] = 4
        wrappers_settings["dilation"] = 1
        wrappers_settings["actions_stack"] = 12
        wrappers_settings["scale"] = True
        wrappers_settings["scale_mod"] = 0

        # Additional obs key list
        key_to_add = []
        key_to_add.append("actions")

        if opt.gameId != "tektagt":
            key_to_add.append("ownHealth")
            key_to_add.append("oppHealth")
        else:
            key_to_add.append("ownHealth1")
            key_to_add.append("ownHealth2")
            key_to_add.append("oppHealth1")
            key_to_add.append("oppHealth2")
            key_to_add.append("ownActiveChar")
            key_to_add.append("oppActiveChar")

        key_to_add.append("ownSide")
        key_to_add.append("oppSide")

        key_to_add.append("ownChar")
        key_to_add.append("oppChar")

        env, num_env = make_stable_baselines_env(time_dep_seed, settings, wrappers_settings,
                                                 key_to_add=key_to_add, p2_mode="integratedSelfPlay",
                                                 use_subprocess=True)

        print("Obs_space = ", env.observation_space)
        print("Obs_space type = ", env.observation_space.dtype)
        print("Obs_space high = ", env.observation_space.high)
        print("Obs_space low = ", env.observation_space.low)

        print("Act_space = ", env.action_space)
        print("Act_space type = ", env.action_space.dtype)
        if settings["action_space"][0] == "multi_discrete":
            print("Act_space n = ", env.action_space.nvec)
        else:
            print("Act_space n = ", env.action_space.n)

        # Policy param
        n_actions = env.get_attr("n_actions")[0][0]
        n_actions_stack = env.get_attr("n_actions_stack")[0]
        n_char = env.get_attr("number_of_characters")[0]
        char_names = env.get_attr("char_names")[0]

        policy_kwargs = {}
        policy_kwargs["n_add_info"] = n_actions_stack*(n_actions[0]+n_actions[1]) +\
            len(key_to_add)-3 + 2*n_char
        policy_kwargs["layers"] = [64, 64]

        policy_kwargs["cnn_extractor"] = local_nature_cnn_small

        print("n_actions =", n_actions)
        print("n_char =", n_char)
        print("n_add_info =", policy_kwargs["n_add_info"])

        # PPO param
        gamma = 0.94
        learning_rate = linear_schedule(2.5e-4, 2.5e-6)
        cliprange = linear_schedule(0.15, 0.025)
        cliprange_vf = cliprange

        # Initialize the model
        model = PPO2Selfplay(CustCnnPolicy, env, verbose=1,
                             gamma=gamma, nminibatches=4, noptepochs=4, n_steps=128,
                             learning_rate=learning_rate, cliprange=cliprange,
                             cliprange_vf=cliprange_vf, policy_kwargs=policy_kwargs)

        print("Model discount factor = ", model.gamma)

        # Create the callback: autosave every USER DEF steps
        auto_save_callback = AutoSave(check_freq=256, num_env=num_env,
                                      save_path=os.path.join(model_folder, "0M_"))

        # Train the agent
        timeSteps = 512
        model.learn(total_timesteps=timeSteps, callback=auto_save_callback)

        # Save the agent
        model_path = os.path.join(model_folder, "512")
        model.save(model_path)
        # Save the correspondent CFG file
        model_cfg_save(model_path, "PPOIntegratedSelfPlaySmall", n_actions, char_names,
                     settings, wrappers_settings, key_to_add)

        # Close the environment
        env.close()

        print("ALL GOOD!")
    except Exception as e:
        print(e)
        print("ALL BAD")
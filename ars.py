# AI 2018 (Compatible with Gym 0.10.5 & PyBullet 2.0.8)

# Importing the required libraries
import os
import numpy as np
import gym
from gym import wrappers
import pybullet_envs  # Ensures PyBullet environments are registered

# Setting Hyperparameters
class Hp():
    def __init__(self):
        self.nb_steps = 1000
        self.episode_length = 1000
        self.learning_rate = 0.02
        self.nb_directions = 16
        self.nb_best_directions = 16
        assert self.nb_best_directions <= self.nb_directions
        self.noise = 0.03
        self.seed = 1
        self.env_name = 'HalfCheetahBulletEnv-v0'

# Normalizing the states
class Normalizer():
    def __init__(self, nb_inputs):
        self.n = np.zeros(nb_inputs)
        self.mean = np.zeros(nb_inputs)
        self.mean_diff = np.zeros(nb_inputs)
        self.var = np.zeros(nb_inputs)
    
    def observe(self, x):
        self.n += 1.
        last_mean = self.mean.copy()
        self.mean += (x - self.mean) / self.n
        self.mean_diff += (x - last_mean) * (x - self.mean)
        self.var = (self.mean_diff / self.n).clip(min=1e-2)
    
    def normalize(self, inputs):
        return (inputs - self.mean) / np.sqrt(self.var)

# Defining Policy
class Policy():
    def __init__(self, input_size, output_size):
        self.theta = np.zeros((output_size, input_size))
    
    def evaluate(self, input, delta=None, direction=None):
        if direction is None:
            return self.theta.dot(input)
        elif direction == "positive":
            return (self.theta + hp.noise * delta).dot(input)
        else:
            return (self.theta - hp.noise * delta).dot(input)
    
    def sample_deltas(self):
        return [np.random.randn(*self.theta.shape) for _ in range(hp.nb_directions)]
    
    def update(self, rollouts, sigma_r):
        step = np.zeros(self.theta.shape)
        for r_pos, r_neg, d in rollouts:
            step += (r_pos - r_neg) * d
        self.theta += hp.learning_rate / (hp.nb_best_directions * sigma_r) * step

# Exploring policy
def explore(env, normalizer, policy, direction=None, delta=None):
    state = env.reset()
    done = False
    num_plays = 0.
    sum_rewards = 0
    while not done and num_plays < hp.episode_length:
        normalizer.observe(state)
        state = normalizer.normalize(state)
        action = policy.evaluate(state, delta, direction)
        state, reward, done, _ = env.step(action)  # Compatible with older Gym versions
        reward = max(min(reward, 1), -1)
        sum_rewards += reward
        num_plays += 1
    return sum_rewards

# Training the AI
def train(env, policy, normalizer, hp):
    for step in range(hp.nb_steps):
        deltas = policy.sample_deltas()
        positive_rewards = [0] * hp.nb_directions
        negative_rewards = [0] * hp.nb_directions
        
        for k in range(hp.nb_directions):
            positive_rewards[k] = explore(env, normalizer, policy, direction="positive", delta=deltas[k])
        
        for k in range(hp.nb_directions):
            negative_rewards[k] = explore(env, normalizer, policy, direction="negative", delta=deltas[k])
        
        all_rewards = np.array(positive_rewards + negative_rewards)
        sigma_r = all_rewards.std()
        
        scores = {k: max(r_pos, r_neg) for k, (r_pos, r_neg) in enumerate(zip(positive_rewards, negative_rewards))}
        order = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:hp.nb_best_directions]
        rollouts = [(positive_rewards[k], negative_rewards[k], deltas[k]) for k in order]
        
        policy.update(rollouts, sigma_r)
        reward_evaluation = explore(env, normalizer, policy)
        print(f'Step: {step}, Reward: {reward_evaluation}')

# Running the main code
def mkdir(base, name):
    path = os.path.join(base, name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

work_dir = mkdir('exp', 'brs')
monitor_dir = mkdir(work_dir, 'monitor')

hp = Hp()
np.random.seed(hp.seed)
env = gym.make(hp.env_name)
env = wrappers.Monitor(env, monitor_dir, force=True)
nb_inputs = env.observation_space.shape[0]
nb_outputs = env.action_space.shape[0]
policy = Policy(nb_inputs, nb_outputs)
normalizer = Normalizer(nb_inputs)
train(env, policy, normalizer, hp)

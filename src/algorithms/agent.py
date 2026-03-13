import random
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=64):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_dim)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class EnsembleDQNAgent:
    def __init__(self, state_dim, action_dim, num_networks=3, lr=1e-3, gamma=0.99, epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.num_networks = num_networks
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_min = epsilon_end
        self.epsilon_decay = epsilon_decay
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.models = [QNetwork(state_dim, action_dim).to(self.device) for _ in range(num_networks)]
        self.optimizers = [optim.Adam(model.parameters(), lr=lr) for model in self.models]
        self.criterion = nn.MSELoss()
        
        self.memory = deque(maxlen=10000)
        self.batch_size = 64

    def select_action(self, state, eval_mode=False):
        if not eval_mode and random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        q_values_list = []
        with torch.no_grad():
            for model in self.models:
                q_values = model(state_tensor)
                q_values_list.append(q_values)
        
        # Ensemble voting or averaging
        # Here: Average Q-values
        avg_q_values = torch.mean(torch.stack(q_values_list), dim=0)
        return torch.argmax(avg_q_values).item()

    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def update(self):
        if len(self.memory) < self.batch_size:
            return
        
        batch = random.sample(self.memory, self.batch_size)
        state_batch, action_batch, reward_batch, next_state_batch, done_batch = zip(*batch)
        
        state_batch = torch.FloatTensor(np.array(state_batch)).to(self.device)
        action_batch = torch.LongTensor(action_batch).unsqueeze(1).to(self.device)
        reward_batch = torch.FloatTensor(reward_batch).unsqueeze(1).to(self.device)
        next_state_batch = torch.FloatTensor(np.array(next_state_batch)).to(self.device)
        done_batch = torch.FloatTensor(done_batch).unsqueeze(1).to(self.device)
        
        for i in range(self.num_networks):
            model = self.models[i]
            optimizer = self.optimizers[i]
            
            q_values = model(state_batch).gather(1, action_batch)
            
            with torch.no_grad():
                next_q_values = model(next_state_batch).max(1)[0].unsqueeze(1)
                target_q_values = reward_batch + (1 - done_batch) * self.gamma * next_q_values
            
            loss = self.criterion(q_values, target_q_values)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

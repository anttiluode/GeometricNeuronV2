import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# Stage 1: Physical Dendritic Cable
# ============================================================
class DendriticBranch:
    def __init__(self, alpha):
        """
        alpha: RC low-pass coefficient. 
        High alpha (~0.9) = Proximal (fast, retains detail)
        Low alpha (~0.1) = Distal (slow, broad spatial context)
        """
        self.alpha = alpha
        self.state = 0.0

    def step(self, x):
        # Cable equation approximation
        self.state = self.alpha * x + (1 - self.alpha) * self.state
        return self.state

# ============================================================
# Core Engine: Geometric Neuron V3
# ============================================================
class GeometricNeuronV3:
    def __init__(self, embed_dim=4, tau=10, theta_freq=2.0, ais_window=15, dt=0.01):
        # Takens Phase-Space Parameters
        self.dim = embed_dim
        self.tau = tau
        self.dt = dt
        
        # Dendritic Array
        self.branch_prox = DendriticBranch(0.9) # Fast/Detail -> Imaginary Axis
        self.branch_dist = DendriticBranch(0.1) # Slow/Context -> Real Axis
        
        # Streaming Buffers
        self.min_len = (self.dim - 1) * self.tau + 1
        self.buffer_prox = []
        self.buffer_dist = []
        
        # The Adaptive Memory (Complex Mosaic)
        self.template = None
        
        # Theta Gate
        self.theta_freq = theta_freq
        self.theta_phase = 0.0
        
        # Physical AIS Window
        self.ais_window = ais_window
        self.ais_buffer = []
        self.baseline_res = 0.0 # Used for dynamic thresholding

    def process(self, x, t_idx):
        """Processes a single float sample in real-time."""
        t = t_idx * self.dt
        
        # 1. Dendritic Routing
        prox = self.branch_prox.step(x)
        dist = self.branch_dist.step(x)
        
        self.buffer_prox.append(prox)
        self.buffer_dist.append(dist)
        
        # Wait until we have enough physical history to fold space
        if len(self.buffer_prox) < self.min_len:
            return 0.0, 0.0, 0.0
            
        # Keep buffers lean
        if len(self.buffer_prox) > self.min_len:
            self.buffer_prox.pop(0)
            self.buffer_dist.pop(0)

        # 2. Takens Embedding (Constructing the Complex Plane)
        # v(t) = Context(Real) + Detail(Imaginary)
        v_prox = np.array([self.buffer_prox[-1 - j*self.tau] for j in range(self.dim)])
        v_dist = np.array([self.buffer_dist[-1 - j*self.tau] for j in range(self.dim)])
        
        v_state = v_dist + 1j * v_prox
        v_norm = v_state / (np.linalg.norm(v_state) + 1e-8)

        # 3. Continuous Learning (Power Iteration on Recurrence Kernel)
        if self.template is None:
            self.template = v_norm
        else:
            # STDP equivalent: Pull the template slightly toward the current recurrent state
            self.template = 0.999 * self.template + 0.001 * v_norm
            self.template /= (np.linalg.norm(self.template) + 1e-8) # Maintain eigenvector

        # 4. Somatic Resonance (Hermitian Inner Product)
        resonance = np.abs(np.vdot(self.template, v_norm))**2

        # 5. Theta Gating (Phase-based Attention)
        theta = max(0, np.sin(2 * np.pi * self.theta_freq * t + self.theta_phase))
        gated_res = resonance * theta

        # 6. AIS Interferometer (Physical Integration Window)
        self.ais_buffer.append(gated_res)
        if len(self.ais_buffer) > self.ais_window:
            self.ais_buffer.pop(0)
            
        # Update dynamic background threshold
        self.baseline_res = 0.99 * self.baseline_res + 0.01 * gated_res
        threshold = self.baseline_res * self.ais_window * 1.5
        
        integral = sum(self.ais_buffer)
        spike = 0.0
        
        # Wavefunction Collapse
        if integral > threshold and len(self.ais_buffer) == self.ais_window:
            spike = 1.0
            self.ais_buffer = [0.0 for _ in range(self.ais_window)] # Refractory snap
            
        return spike, resonance, integral

# ============================================================
# LIVE TEST: The Adaptive Organism
# ============================================================
if __name__ == "__main__":
    T = 3000
    dt = 0.01
    t_arr = np.arange(T) * dt
    
    # Generate an environment with a stable structure and an anomaly
    # Baseline: Slow 1Hz wave + Fast 8Hz detail
    x = np.sin(2 * np.pi * 1.0 * t_arr) + 0.4 * np.sin(2 * np.pi * 8.0 * t_arr)
    x += np.random.normal(0, 0.1, T) # Biological noise
    
    # Inject a massive anomaly at t=1500 (sudden frequency and amplitude shift)
    x[1500:1700] += 2.0 * np.sin(2 * np.pi * 15.0 * t_arr[1500:1700])

    # Boot up the V3 Neuron
    gn = GeometricNeuronV3(embed_dim=4, tau=15, theta_freq=2.0, ais_window=10, dt=dt)
    
    spikes, resonances, integrals = [], [], []
    
    # Stream the data in real-time (No backprop, no batching)
    for i in range(T):
        s, r, intg = gn.process(x[i], i)
        spikes.append(s)
        resonances.append(r)
        integrals.append(intg)

    # Plot the results
    fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
    
    axs[0].plot(t_arr, x, color='gray')
    axs[0].set_title("1. Raw Environmental Wave (Note the anomaly at t=15.0s)")
    
    axs[1].plot(t_arr, resonances, color='purple')
    axs[1].set_title("2. Geometric Resonance (Hermitian Inner Product)")
    
    axs[2].plot(t_arr, integrals, color='black')
    axs[2].axhline(y=np.mean(integrals)*1.5, color='red', linestyle='--', alpha=0.5, label="Dynamic Threshold")
    axs[2].set_title("3. Physical AIS Integration (The Roll)")
    axs[2].legend(loc="upper right")
    
    spike_times = t_arr[np.array(spikes) == 1.0]
    axs[3].vlines(spike_times, ymin=0, ymax=1, color='red', linewidth=2)
    axs[3].set_title("4. Discrete Spikes (The Snap)")
    
    plt.xlabel("Time (seconds)")
    plt.tight_layout()
    plt.show()
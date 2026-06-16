import numpy as np
import math

class UnivacIXLogisticsTracker:
    def __init__(self):
        # ─── UNIVERSAL PHYSICAL CONSTANTS ───
        self.c = 299792458.0          # Speed of light (m/s)
        self.k_B = 1.380649e-23       # Boltzmann's Constant (J/K)
        self.mu_0 = 4 * math.pi * 1e-7 # Magnetic permeability of free space
        
        # ─── SYSTEM BAND SPECIFICATIONS (BLUETOOTH 5.4 / SEAWATER / SATELLITE) ───
        self.f_bluetooth = 2441.0 * 1e6 # Center Bluetooth frequency (Hz)
        self.f_vlf = 24.8 * 1e3         # VLF frequency like Jim Creek (Hz)
        self.b_ble = 1.0 * 1e6          # BLE single channel bandwidth (Hz)
        self.nvp_cable = 0.67           # Nominal Velocity of Propagation (Cat6 Ethernet)
        
        # ─── THREE-VALUED LOGIC (3VL) DEFINITIONS ───
        self.3VL_TRUE = 1.0
        self.3VL_FALSE = 0.0
        self.3VL_INDETERMINATE = 0.5

    # ─── 1. TIME-DOMAIN & CHANNEL SOUNDING FUNCTIONS ───
    def calculate_ethernet_tdr_length(self, time_seconds):
        """Equation 2 & 6: Time-Domain Reflectometry for Link Integrity"""
        v = self.nvp_cable * self.c
        length_meters = (v * time_seconds) / 2.0
        return length_meters

    def calculate_bluetooth_channel_sounding_distance(self, delta_phase, delta_freq):
        """Bluetooth Channel Sounding Ranging Equation"""
        distance = (self.c * delta_phase) / (4.0 * math.pi * delta_freq)
        return distance

    # ─── 2. RF ATTENUATION, NOISE, AND INTERFERENCE ENGINES ───
    def evaluate_thermal_noise_floor(self, temperature_kelvin):
        """Thermal Noise Power Equation (dBm)"""
        p_n_watts = self.k_B * temperature_kelvin * self.b_ble
        p_n_dBm = 10 * math.log10(p_n_watts / 0.001)
        return p_n_dBm

    def calculate_attenuation_db(self, p_in, p_out):
        """Standard Loss Formula (dB)"""
        return 10 * math.log10(p_in / p_out)

    def calculate_log_distance_path_loss_rssi(self, distance, p_tx, env_n, reference_dist=1.0):
        """Log-Distance Path Loss Model for Real-World Environments"""
        # Calculate standard FSPL reference baseline at 1 meter
        fspl_ref = 20 * math.log10(reference_dist) + 20 * math.log10(self.f_bluetooth / 1e6) - 27.55
        rssi_predicted = p_tx - (fspl_ref + 10 * env_n * math.log10(distance / reference_dist))
        return rssi_predicted

    def estimate_distance_from_rssi(self, rssi, measured_power_at_1m, env_n):
        """Inverse Log-Distance Model used for raw RSSI tracking"""
        return 10 ** ((measured_power_at_1m - rssi) / (10.0 * env_n))

    def compute_sinr_or_sinr(self, p_signal, p_noise, p_interference_sum):
        """Signal-to-Interference-plus-Noise Ratio (SINR)"""
        return p_signal / (p_noise + p_interference_sum)

    def calculate_shannon_mimo_capacity(self, mimo_streams, bandwidth, sinr_linear):
        """Shannon-Hartley Maximum Channel Capacity Bound with MIMO Scaling"""
        return mimo_streams * bandwidth * math.log2(1.0 + sinr_linear)

    # ─── 3. HIGH-VELOCITY DYNAMICS & ADVANCED PHYSICS ───
    def calculate_doppler_shift(self, f_transmitted, relative_velocity):
        """Doppler Shift Correction for LEO Satellites or High-Speed Rail"""
        return f_transmitted * (1.0 - (relative_velocity / self.c))

    def calculate_wien_displacement_wavelength(self, temperature_kelvin):
        """Wien's Displacement Law: Peak Thermal IR emission of tracked assets"""
        wien_constant = 2.897771955e-3
        return wien_constant / temperature_kelvin

    def calculate_stefan_boltzmann_power(self, emissivity, area, temperature_kelvin):
        """Stefan-Boltzmann Law: Total Radiant Thermal Energy Blasted by Asset"""
        sigma = 5.670374419e-8
        return emissivity * sigma * area * (temperature_kelvin ** 4)

    def calculate_seawater_skin_depth(self, frequency, conductivity_seawater=4.0):
        """Skin Effect Equation: VLF Transmission Depth (e.g., Jim Creek Submarine Link)"""
        omega = 2.0 * math.pi * frequency
        skin_depth = math.sqrt(2.0 / (omega * self.mu_0 * conductivity_seawater))
        return skin_depth

    # ─── 4. UNIVAC THREE-VALUED LOGIC (3VL) GATE SYSTEM ───
    def univac_3vl_and(self, state_a, state_b):
        """UNIVAC 3VL AND Gate: min(A, B)"""
        return min(state_a, state_b)

    def univac_3vl_or(self, state_a, state_b):
        """UNIVAC 3VL OR Gate: max(A, B)"""
        return max(state_a, state_b)

    def univac_3vl_not(self, state_a):
        """UNIVAC 3VL NOT Gate: 1 - A"""
        return 1.0 - state_a

    def validate_packet_telemetry_3vl(self, rssi, p_noise_floor):
        """Uses Kleene Algebra to classify if raw signal is True, False, or Cosmic Interference"""
        if rssi > (p_noise_floor + 15.0): # Safe margin above noise floor
            return self.3VL_TRUE
        elif rssi <= p_noise_floor:
            return self.3VL_FALSE
        else:
            return self.3VL_INDETERMINATE # Signal is lost or corrupted in noise

    # ─── 5. THE 3D MULTILATERATION SOLVER ENGINE ───
    def solve_3d_trilateration(self, anchors, distances):
        """
        Calculates exact Cartesian (x, y, z) coordinates using Linear Multi-Sphere Matrix Intersection.
        
        anchors: Dict or list of tuples containing known locations [(x1,y1,z1), (x2,y2,z2)...]
        distances: List of calculated distances from asset to corresponding anchor nodes.
        """
        num_anchors = len(anchors)
        if num_anchors < 4:
            raise ValueError("Trilateration requires a minimum of 4 anchors to compute an absolute 3D position vector.")

        A_matrix = []
        b_vector = []

        # Anchor 1 acts as our relative origin transformer matrix boundary (x1, y1, z1)
        x1, y1, z1 = anchors[0]
        d1 = distances[0]

        for i in range(1, num_anchors):
            xi, yi, zi = anchors[i]
            di = distances[i]

            # Construct row elements for Matrix A: 2(xi - x1), 2(yi - y1), 2(zi - z1)
            row_A = [2 * (xi - x1), 2 * (yi - y1), 2 * (zi - z1)]
            A_matrix.append(row_A)

            # Construct row element for Column Vector b: (d1^2 - di^2) - (x1^2 - xi^2) - (y1^2 - yi^2) - (z1^2 - zi^2)
            element_b = (d1**2 - di**2) - (x1**2 - xi**2) - (y1**2 - yi**2) - (z1**2 - zi**2)
            b_vector.append(element_b)

        # Convert to rigorous NumPy floating-point matrices
        A = np.array(A_matrix, dtype=float)
        b = np.array(b_vector, dtype=float)

        # Use Moore-Penrose Pseudo-Inverse (Least Squares) optimization solver to handle multi-anchor mesh discrepancies
        coordinates_xyz = np.linalg.pinv(A).dot(b)
        return coordinates_xyz

# ─── 6. RUNTIME SIMULATION TEST IN THE UNIVAC-IX PIPELINE ───
if __name__ == "__main__":
    tracker = UnivacIXLogisticsTracker()
    print("=== UNIVAC-IX CARTEZIAN GEOMETRY SPATIAL MESH ENGINE RUNNING ===")

    # Define fixed physical Bluetooth anchor nodes mounted on warehouse ceiling / space payload frames
    # Formatting: (x, y, z) in meters
    anchors = [
        (0.0, 0.0, 5.0),    # Anchor 1 (Origin ceiling corner)
        (20.0, 0.0, 5.0),   # Anchor 2
        (0.0, 30.0, 6.0),   # Anchor 3
        (20.0, 30.0, 4.5)   # Anchor 4
    ]

    # Target configuration properties for real-world environment mapping
    env_path_loss_exponent = 2.7   # Factory warehouse environment profile (n-coefficient)
    measured_power_1m = -58.0      # Calibrated hardware power reference (A)
    device_temp_celsius = 25.0     # Target device monitoring status
    temp_kelvin = device_temp_celsius + 273.15

    # Measure the background thermal limits of the operations room
    calculated_noise_floor = tracker.evaluate_thermal_noise_floor(temp_kelvin)
    print(f"System Thermal Noise Floor Calculation Limit: {calculated_noise_floor:.2f} dBm")

    # Raw incoming telemetry collected from individual Bluetooth receiver interfaces
    raw_rssi_stream = [-72.5, -81.2, -78.4, -84.0]
    
    # Run Univac 3VL Telemetry Integrity Filter
    valid_pulses = []
    for idx, rssi_val in enumerate(raw_rssi_stream):
        validity = tracker.validate_packet_telemetry_3vl(rssi_val, calculated_noise_floor)
        if validity == tracker.3VL_TRUE:
            valid_pulses.append(rssi_val)
        elif validity == tracker.3VL_INDETERMINATE:
            print(f"Warning: Anchor {idx+1} signal flagged as INDETERMINATE by Kleene 3VL Logic. Proceeding with caution.")
            valid_pulses.append(rssi_val)

    # Convert live physical wave constraints into distances via Inverse Log-Distance Model
    calculated_distances = [
        tracker.estimate_distance_from_rssi(rssi, measured_power_1m, env_path_loss_exponent)
        for rssi in raw_rssi_stream
    ]
    
    for idx, dist in enumerate(calculated_distances):
        print(f"Computed Vector Distance to Node {idx+1}: {dist:.3f} meters")

    # Execute Moore-Penrose Multilateration to map true 3D spatial location vector
    try:
        calculated_3d_position = tracker.solve_3d_trilateration(anchors, calculated_distances)
        print("\n-------------------------- RESULT --------------------------")
        print(f"Target Resolved Coordinates Vector -> X: {calculated_3d_position[0]:.3f}m, Y: {calculated_3d_position[1]:.3f}m, Z: {calculated_3d_position[2]:.3f}m")
        print("------------------------------------------------------------")
    except Exception as error_msg:
        print(f"Spatial Matrix Solver Fault: {error_msg}")

    # Display additional tracked properties processed inside the Univac-IX module framework
    peak_ir = tracker.calculate_wien_displacement_wavelength(temp_kelvin)
    print(f"Asset Surface Thermal Spectrum Peak Output Wavelength: {peak_ir * 1e6:.3f} micrometers")
    
    jim_creek_depth = tracker.calculate_seawater_skin_depth(tracker.f_vlf)
    print(f"Reference Signal VLF Skin-Depth Absorption Limit (Jim Creek standard): {jim_creek_depth:.2f} meters")

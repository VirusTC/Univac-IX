import numpy as np

class UnivacLightProcessor:
    def __init__(self, refractive_index_datasource):
        # This dictionary mimics your compiled JSON dependency graph from Excel
        self.db = refractive_index_datasource 
        self.c = 299792458  # Speed of light in m/s

    def analyze_light_input(self, time_of_flight, input_power, element, state_vars):
        """
        Calculates the complete structural topology of the light path
        """
        # Fetch dynamic variables calculated via the sheet's formula graph
        n = self.db.get_refractive_index(element, state_vars['electrons'], state_vars['charge'])
        alpha = self.db.get_attenuation_coeff(element)
        
        # 1. Distance Calculation
        distance = (self.c * time_of_flight) / (2 * n)
        
        # 2. Attenuation / Power Loss Profile
        attenuation_loss = input_power * (1 - np.exp(-alpha * distance))
        
        return {
            "calculated_distance_meters": distance,
            "attenuation_loss_db": 10 * np.log10(input_power / (input_power - attenuation_loss)),
            "effective_refractive_index": n
        }

    def detect_and_cancel_noise(self, raw_signal, background_noise_profile):
        """
        Advanced Wave Optical Noise Cancellation
        Samples background noise and applies destructive phase interference
        """
        # Fourier Transform to shift from time/spatial domain to frequency domain
        signal_fft = np.fft.fft(raw_signal)
        noise_fft = np.fft.fft(background_noise_profile)
        
        # Surgical Noise Cancellation subtracting the exact noise profile magnitude
        clean_fft = signal_fft - noise_fft
        
        # Inverse Fourier Transform back to reconstruct the pristine light wave
        pristine_signal = np.fft.ifft(clean_fft)
        return np.real(pristine_signal)

    def analyze_imperfections(self, signal_reflection_array, n_medium):
        """
        Scans for Splices, Air Bubbles, and End-Face Quality
        """
        events = []
        for index, r_coefficient in enumerate(signal_reflection_array):
            if r_coefficient > 0.04:  # Reflection threshold matching glass-to-air transition
                # Calculate if the event is an air bubble cavity (n boundary approaches 1.0)
                n_anomaly = n_medium * ((1 - np.sqrt(r_coefficient)) / (1 + np.sqrt(r_coefficient)))
                if np.isclose(n_anomaly, 1.0, atol=0.1):
                    events.append({"index": index, "type": "Air Bubble / Void Cavity Detected"})
                else:
                    events.append({"index": index, "type": "Mechanical Splice / Connector"})
                    
        return events

    def calculate_pigment_color(self, element, electrons, charge):
        """
        Processes your final Excel column logic: Maps element state to exact visible color
        """
        # 1. Determine quantum energy gap based on chemical state inputs
        energy_gap_joules = self.db.calculate_energy_gap(element, electrons, charge)
        
        # 2. Physics: Calculate target emission wavelength (Planck-Einstein relation)
        h = 6.62607015e-34  # Planck's constant
        wavelength_nm = (h * self.c / energy_gap_joules) * 1e9
        
        # 3. Spectrum to RGB Mapping (CIE Color Space Conversion Approximation)
        rgb = self._wavelength_to_rgb(wavelength_nm)
        return {"wavelength_nm": wavelength_nm, "hex_color": rgb}

    def _wavelength_to_rgb(self, w):
        # Canonical algorithmic conversion of nanometer spectrum to hardware RGB
        if 380 <= w < 440: R, G, B = -(w - 440)/(440 - 380), 0.0, 1.0
        elif 440 <= w < 490: R, G, B = 0.0, (w - 440)/(490 - 440), 1.0
        elif 490 <= w < 510: R, G, B = 0.0, 1.0, -(w - 510)/(510 - 490)
        elif 510 <= w < 580: R, G, B = (w - 510)/(580 - 510), 1.0, 0.0
        elif 580 <= w < 645: R, G, B = 1.0, -(w - 645)/(645 - 580), 0.0
        elif 645 <= w <= 781: R, G, B = 1.0, 0.0, 0.0
        else: R, G, B = 0.0, 0.0, 0.0
        return f"#{int(R*255):02x}{int(G*255):02x}{int(B*255):02x}"

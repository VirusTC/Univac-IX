graph TD
    %% Define System Input Channels
    subgraph Legacy_Hardware_Chassis [55-Port Legacy Hardware Input Cage]
        P1_16[Ports 01-16: NTDS Parallel<br/>MIL-STD-1397 Type A/B/C<br/>0V to -15V Differential Radar/Aegis]
        P17_32[Ports 17-32: NTDS Serial<br/>MIL-STD-1397 Type D/E<br/>Synchronous Triaxial Telemetry]
        P33_44[Ports 33-44: Asynchronous TTY<br/>Uniscope 100/200 Terminals<br/>RS-232 / RS-422 Interface]
        P45_52[Ports 45-52: 36-Bit Word DMA<br/>UNIVAC 1100 Memory Backplane<br/>Discrete Backplane Card Cages]
        P53_55[Ports 53-55: Industrial Bus<br/>Facility Alarms & Lift Relays<br/>Half-Duplex RS-485 Multidrop]
    end

    %% Define Hardware Ingestion Layer
    subgraph Physical_Ingestion_Fabric [Multi-Interface Hardware Breakout Layer]
        FPGA_Serial[PCIe / Multi-Port USB FPGA Serializer Card Array<br/>Converts Parallel Voltages to Sequential Byte Arrays]
        Multiplexer[55-Channel Scanning Multiplexer Loop<br/>Polling Frequency: 200 Hz Matrix Window]
    end

    %% Define Software Computation Core
    subgraph Computation_Core [UNIVAC-IX Processing Core Engine]
        Numba_CPU[Numba Multicore CPU Ingestion Fabric<br/>@njit Cache Parallel Processing Array]
        CUDA_GPU[NVIDIA CUDA Parallelization Acceleration Matrix<br/>Streaming Multiprocessor Inversion Kernels]
        Heuristic_Learn[Heuristic Pattern Recognition Layer<br/>Autonomic Learning Signature Identification]
    end

    %% Define System Output Interfaces
    subgraph Output_Trunk_Interfaces [High-Density Enterprise Aggregation Layer]
        Fiber_Trunk[High-Speed Fiber Optic Backbone Trunk Line<br/>10GbE SFP+ Interface Proxy Server Node<br/>Address Mapped Space: 0x00FF]
    end

    %% Define Recovery Destination Targets
    subgraph Downstream_Recovery_Targets [Emergency Operational Action Nodes]
        KVM_GUI[Univac_Sperry_KVM_GUI Dashboard<br/>Live Variable Inject Manifestation]
        Visio_Log[Microsoft Visio Data Visualizer Spreadsheet<br/>Dynamic Color Code & Structural CSV Schema]
        Radio_TX[Port 20: Radio_Transmission_Out<br/>Long-Range Over-The-Air Telemetry SMS Trap]
    end

    %% Connect Architecture Pathways
    P1_16 --> FPGA_Serial
    P17_32 --> FPGA_Serial
    P33_44 --> FPGA_Serial
    P45_52 --> Multiplexer
    P53_55 --> Multiplexer
    
    FPGA_Serial --> Multiplexer
    Multiplexer -->|Raw Hexadecimal Streams| Numba_CPU
    Multiplexer -->|Massive Block Image Files| CUDA_GPU
    
    Numba_CPU --> Heuristic_Learn
    CUDA_GPU --> Heuristic_Learn
    
    Heuristic_Learn -->|Aggregated Protocol Packets| Fiber_Trunk
    
    Fiber_Trunk -->|Live Variable Injections| KVM_GUI
    Fiber_Trunk -->|State Compliance Auditing| Visio_Log
    Fiber_Trunk -->|Emergency Handshake Payloads| Radio_TX
    
    %% Style Blocks for Enterprise Presentation
    classDef inputs fill:#1f2937,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef hardware fill:#111827,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef software fill:#312e81,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef outputs fill:#064e3b,stroke:#ec4899,stroke-width:2px,color:#fff;
    classDef targets fill:#4c1d95,stroke:#ef4444,stroke-width:2px,color:#fff;
    
    class P1_16,P17_32,P33_44,P45_52,P53_55 inputs;
    class FPGA_Serial,Multiplexer hardware;
    class Numba_CPU,CUDA_GPU,Heuristic_Learn software;
    class Fiber_Trunk outputs;
    class KVM_GUI,Visio_Log,Radio_TX targets;

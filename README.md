# Cyber Range Experiments: LLM-Guided Attack Automation

[![CCF-C](https://img.shields.io/badge/CCF-C-blue)](https://www.ccf.org.cn/)
[![SCI Q2](https://img.shields.io/badge/SCI-Q2-green)]()

This repository contains the experiment scripts, data, and platform code for the paper:

**"A Cyber Range Platform with Principled LLM-Guided Attack Automation: Theory, Implementation, and Experiments"**

Submitted to *Journal of Information Security and Applications* (JISA), Elsevier, 2026.

## Repository Structure

```
├── README.md                          # This file
├── exp_noise_grid.py                  # Noise grid experiment (30 conditions)
├── exp_chain_depth.py                 # Chain depth amplification (H=1-5)
├── exp_5step.py                       # 5-step attack chain experiment
├── exp_regret_scaling.py              # Regret vs sqrt(T) scaling
├── exp_regret_v2.py                   # Regret scaling v2 with proper Bayesian regret
├── exp_i_llm_expanded.py             # I_LLM measurement across 6 CTF categories
├── exp_cross_model.py                 # Cross-model I_LLM comparison (NVIDIA API)
├── exp_temperature_sweep.py           # Temperature robustness sweep
├── exp_robustness.py                  # Prompt rephrasing + action shuffling robustness
├── exp_lambda_sweep.py                # Lambda prior-weight sensitivity
├── exp_statistical.py                 # Statistical validation of claims
├── exp_real_vuln_v2.py               # Real vulnerable service experiment
├── exp_real_vuln_service.py           # Real attack chain experiment v2
├── exp_transfer.py                    # Cross-task transfer (Web->PWN)
├── generate_figures.py                # Figure generation (original)
├── generate_figures_v2.py             # Figure generation (optimized)
├── figures_nature.py                  # Figure generation (nature-figure style)
├── llm_gateway.py                     # LLM Gateway (FastAPI, port 8000)
├── deploy_scenarios.sh                # OVS + Docker deployment script
├── vuln_service.py                    # Custom vulnerable web service
├── network_benchmark.py               # OVS network performance benchmarks
├── results/                           # All experimental result JSON files
│   ├── noise_grid.json
│   ├── chain_depth.json
│   ├── exp_5step.json
│   ├── regret_scaling_v2.json
│   ├── i_llm_expanded.json
│   ├── cross_model_illm.json
│   ├── temperature_sweep.json
│   ├── robustness.json
│   ├── lambda_sweep.json
│   ├── real_exploit_calibration.json
│   ├── real_attack_chain.json
│   └── ...
└── states/                            # LLM prior measurement states
    └── illm_states.json
```

## Key Experiments

| Experiment | Script | Data | Description |
|-----------|--------|------|-------------|
| Noise Grid | exp_noise_grid.py | results/noise_grid.json | 30 (pg, pb) combinations × 3 T values |
| Chain Depth | exp_chain_depth.py | results/chain_depth.json | H=1-5 chain amplification |
| 5-Step Chain | exp_5step.py | results/exp_5step.json | Real-LLM-prior heterogeneous chain |
| Regret Scaling | exp_regret_v2.py | results/regret_scaling_v2.json | Bayesian regret vs sqrt(T) |
| I_LLM Measurement | exp_i_llm_expanded.py | results/i_llm_expanded.json | 6 categories × 18 states |
| Cross-Model I_LLM | exp_cross_model.py | results/cross_model_illm.json | 4 NVIDIA models comparison |
| Temperature Sweep | exp_temperature_sweep.py | results/temperature_sweep.json | I_LLM stability across τ |
| Prompt Robustness | exp_robustness.py | results/robustness.json | Rephrasing + action shuffling |
| Lambda Sensitivity | exp_lambda_sweep.py | results/lambda_sweep.json | Prior weight λ sweep |
| Cross-Task Transfer | exp_transfer.py | results/transfer.json | Web->PWN transfer |
| Network Benchmarks | network_benchmark.py | results/network_benchmarks.json | OVS latency, throughput, isolation |
| Real-Service Calibration | exp_real_vuln_v2.py | results/real_attack_chain.json | HTTP exploit determinism test |

## Platform

- **LLM Gateway**: FastAPI (Python 3.10) on port 8000
- **LLM Backend**: DeepSeek-V4-Pro (via DeepSeek API)
- **Network**: Open vSwitch 3.3.4 with per-scenario bridges
- **Containers**: Docker 29.1.3

## Reproduction

1. Deploy OVS scenarios: `bash deploy_scenarios.sh`
2. Start LLM Gateway: `python3 llm_gateway.py`
3. Run any experiment: `python3 exp_<name>.py`
4. Results are saved to `results/` directory

## License

MIT License

## Citation

```bibtex
@article{zhou2026cyber,
  title={A Cyber Range Platform with Principled LLM-Guided Attack Automation: Theory, Implementation, and Experiments},
  author={Zhou, Zhiqiang and Wang, Chenlin and Zhang, Yanbin},
  journal={Journal of Information Security and Applications},
  year={2026},
  note={Submitted}
}
```

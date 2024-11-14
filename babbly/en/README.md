# Babbly

## English mode

![Babbly banner](../../images/Babbly_banner.png)
**Beautiful** in flaws, **Artificial incompetence** remains our **Buddy**, **Bypassing** threats while **Leaving** us **Yearning** for growth.

---

## Details of Tools

**Babbly** is a unique penetration testing support tool equipped with **Artificial Incompetence** instead of AI. It operates fully offline and on-premise, meaning no internet connection is required. This flexibility allows it to be implemented in environments where confidentiality is critical or systems with special constraints, all without risk. Below are the main features of Babbly and the environments where it can be utilized.

### Key Features and Selling Points

1. Intuitive Conversational Interface with Artificial Incompetence
   Babbly uses "Artificial Incompetence" instead of AI. This enables a simple conversational interface that operates stably, without relying on learning or accuracy. It is designed for easy use even by beginners, with no complex adjustments required.
2. Flexible Test Execution Based on SOPs (Standard Operating Procedures)
   Babbly allows users to register test procedures according to their company's regulations, following SOPs. This enables the execution of tests that comply with company-specific guidelines, along with customizable scenario settings.
3. Eyes-Free, Hands-Free Operation
   With voice recognition, tests can be executed with voice commands alone. There’s no need to focus on the screen, enabling tests to be conducted efficiently alongside other tasks.
4. Simple Target and Attack Scenario Setup
   Targets and attack scenarios can be specified with simple operations, allowing even beginners to conduct penetration tests flexibly.
5. Instant Notification of Results
   Test results can be instantly confirmed through voice or screen notifications, making it easier to understand the status in real-time.
6. High Cost-Performance and Environmental Adaptability
   Since Babbly operates offline, it offers lower costs compared to AI-based online tools, and can be flexibly implemented in specialized environments.

### Suitable Environments and Use Cases

Babbly can be used flexibly in environments where internet access is restricted, such as:  

- **Isolated Network Environments**: Testing in high-security facilities like military bases or nuclear power plants that are disconnected from external networks.
- **On-Site Security Evaluation**: Quick security assessments in remote or disaster-stricken areas.
- **EMP Resistance Testing**: Assessing infrastructure resistance in EMP shielded rooms under extreme conditions.
- **Onboard Systems in Aircraft or Ships**: Security checks in environments where external networks cannot be accessed during flight or navigation.
- **Off-Grid Systems**: Security testing for independent microgrids or remote communication stations.
- **Privacy-Focused Environments**: Internal assessments in environments that require total data protection, such as medical or financial institutions.
- **Industrial Control Systems (ICS)**: Testing of isolated control systems in factories or infrastructure facilities.
- **Testing in Radio-Controlled Zones**: Security assessments in areas where radio waves are restricted.
- **Disaster Network Evaluation**: Security checks in temporary networks during disasters.
- **Training in Educational Institutions**: Providing practical, offline training in a safe learning environment.
- **Compliance-Driven Environments**: Evaluation of medical or financial systems in compliance with HIPAA or PCI DSS.
- **Testing Standalone IoT Devices**: Security checks for independent IoT devices (e.g., industrial sensors) that do not require internet connections.

### Differentiation from AI-Based Tools

Babbly eliminates the need for online connections or data dependence, providing lower-cost, high-reliability performance. It doesn't rely on the precision or learning results typical of AI tools and offers tests based on SOPs, tailored to company standards. Babbly allows efficient testing in high-security or specialized environments with flexibility and reliability.

---

## Setup

1. Install to `libttspico-utils`.  

   ``` bash
   sudo apt update
   sudo apt install libttspico-utils
   ```

2. Download vosk model  

   | Model | Size | Word error rate/Speed | Notes | License |
   | ---- | ---- |---- | ---- |---- |
   | [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip) | 40M | 9.85 (librispeech test-clean) 10.38 (tedlium) | Lightweight wideband model for Android and RPi| Apache 2.0 |
   | [vosk-model-en-us-0.22](https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip) | 1.8G | 5.69 (librispeech test-clean) 6.05 (tedlium) 29.78(callcenter) | Accurate generic US English model| Apache 2.0 |

   *The Vosk model works fine even with the small version.*

3. Rename the downloaded Vosk model to `model` and place it in the `Babbly/babbly/en/` directory.  

   ``` bash
   mv vosk-model-small-en-us-0.15 /home/kali/Babbly/babbly/en/model
   ```

4. Open the configuration file (`babbly/en/config_en.yaml`) and edit **WAKEUP_PHRASE** and **EXIT_PHRASE**. Do not make any other changes.  
   *I recommend using a wake-up phrase that is easy to call and recognize (I wanted to use "Babbly," but it is not recognized well, so please choose a name you like).*

   ``` yaml
   WAKEUP_PHRASE: "friday"
   EXIT_PHRASE: "exit"
   COMMANDS_PATH: "babbly/en/commands.txt"
   TARGETS_PATH: "babbly/en/targets.json"
   SOP_PATH: "babbly/en/sop.json"
   MODEL_PATH: "babbly/en/model"
   ```

## How to use

1. Run `babbly_en.py`.
2. When the voice announces the start of the system, say the wake-up phrase.
3. When the wake-up phrase is recognized, it will enter a command-waiting state, so please give a command. (e.g., "Scan the network.")
4. For example, if you command a network scan, the program will accept the command, execute the Nmap command internally, and report the discovered hosts.
5. After completing the network scan, the IP addresses of the discovered hosts are recorded as target information in `targets.json`.
6. To end, please say the exit phrase while in the command-waiting state.

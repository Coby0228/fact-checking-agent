# DelphiAgent

We propose **DelphiAgent**, an innovative agentic framework for trustworthy fact-checking that employs multiple LLMs to emulate the workflow of the Delphi method. Our goal is to enhance transparency in the decision-making procedure and mitigate hallucinations when generating justifications.

DelphiAgent is implemented through a dual-system framework that integrates two main modules:

- **Evidence Mining Module**  
  This module extracts evidence from raw, uncensored reports and refines it, ensuring the provision of instructive rationales for subsequent processing.

- **Delphi Decision-Making Module**  
  Drawing inspiration from the Delphi method, this module devises multiple LLM-based agents with distinct personalities. Each agent independently makes factuality judgments based on the claim and its verified evidence. Through multiple rounds of feedback and synthesis, the system reaches a consensus.

![DelphiAgent Framework](./path/to/your/image.jpg)

## Installation

Install the required package using pip:

```bash
pip install autogen-agentchat~=0.2
```
## Datasets

- The self-constructed **GuardEval** dataset has been uploaded to the `dataset` directory.
- For the **RAWFC** and **LIAR-RAW** datasets, please refer to the GitHub repository: [GitHub Repository](https://github.com/Nicozwy/CofCED)

## Error Cases
Due to space constraints in the paper, we are unable to display the failure case. Therefore, the complete failure case is available on GitHub.
The failure case analysis revealed certain limitations of the proposed DelphiAgent method when applied to fine-grained labeling tasks. The fine-grained nature of labels such as "Half-True" and "Barely-True" makes it challenging for fact-checkers to reach a consensus.
In the first round, all fact-checkers agreed that the claim regarding a 50% increase in emergency room visits was not fully supported. While they acknowledged an increase in ER visits following the ACA, the specific figure of 50% was contested. Fact Checker 1 rated the claim as "Half-True," while Fact Checkers 2 and 3 rated it as "Barely-True."
In the second round, consensus emerged that the 50% increase was exaggerated and lacked universal support. Most fact-checkers agreed that there had been an increase in emergency room visits post-ACA, but the classifications varied. Two fact-checkers rated the claim as "Half-True," while one rated it as "Barely-True."
In the third round, Fact Checkers 1 and 2 rated the claim as "Half-True," acknowledging an increase in emergency room visits but criticizing the 50% figure as exaggerated. Fact Checker 3 rated the claim as "Barely-True," suggesting that the claim was even more misleading than the first two fact-checkers had recognized.
In the final round, all fact-checkers agreed on the classification of "Half-True," reaching a consensus that the claim was partially correct regarding the increase in emergency room visits, but disagreed on the validity of the 50% increase, which was seen as exaggerated or misleading.
When comparing the justifications produced by DelphiAgent to the corresponding ground-truth explanations, although DelphiAgent incorrectly predicted the claim as "Half-True," it successfully identified the inaccuracies and misleading aspects within the claim.
![Faliure case.](./path/to/your/image.jpg)
## Citation
If you use our framework or datasets in your research, please cite our work. 

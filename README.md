# H1 Project Goals
- Software should take pipeline input then output report
- Make software pipeline agnostic

Input: Pipeline run URL / ID 
Output:
    - Failed stage/job/step
    - Error summary
    - Root cause hypothesis
    - Suggested fix
    - Relevant file/code references (repo)
    - Optional PR comment or issue creation

Node Flow
1. Parse user input
2. Detect pipeline platform
3. Fetch pipeline
4. Normalize pipeline
5. Extract error context
6. Classify failure
7. Retrieve repository context
8. Analyze root cause
9. Suggest fix
10. Generate report from previous steps
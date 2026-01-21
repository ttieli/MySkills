---
name: generate-ralph
description: Automates the setup of a Ralph Loop environment (scripts + planning files) for any given task. Use when the user wants to start a new complex coding loop.
---

# Meta-Skill: Generate Ralph Loop

**Objective**: Create a robust, self-correcting development loop for the user's specific task.

**Input**: The user's task description (e.g., "Write a Snake game in Python").

**Actions Required**:

1.  **Analyze the Request**: Understand what language, framework, or tools are needed.
2.  **Create `task_plan.md`**:
    *   Initialize with clear Phases (Initialization, Implementation, Testing, Refinement).
    *   Set the "Goal" to match the user's request.
3.  **Create `findings.md` & `progress.md`**: Initialize as empty/template files.
4.  **Create `ralph_loop.sh`**:
    *   Generate a bash script that loops indefinitely.
    *   Include a `claude` CLI call that feeds errors back to the model.
    *   Ensure the script checks for a "Completion Condition" (e.g., tests passing or a specific file existing).

**Template for `ralph_loop.sh` (Customize this!)**:
```bash
#!/bin/bash
# Ralph Loop for: {{TASK_NAME}}

MAX_LOOPS=30
CURRENT_LOOP=0

echo "🚀 Starting Ralph Loop for {{TASK_NAME}}..."

while [ $CURRENT_LOOP -lt $MAX_LOOPS ]; do
    let CURRENT_LOOP=CURRENT_LOOP+1
    echo "🔄 Loop Iteration: $CURRENT_LOOP"

    # Define your verification command here (e.g., run tests, run script)
    # For now, we ask Claude to determine what to run based on the plan.
    
    claude "You are in a Ralph Loop for '{{TASK_NAME}}'. 
    Current Phase: Check 'task_plan.md'.
    
    Your Goal:
    1. If code exists, Run it/Test it.
    2. If it fails, Fix it.
    3. If it doesn't exist, Create it.
    4. Update 'progress.md' and 'task_plan.md'.
    
    If the task is fully complete (all checkboxes in task_plan are checked), output 'ALL DONE' to stdout." > output.log 2>&1
    
    # Check for completion signal
    if grep -q "ALL DONE" output.log; then
        echo "🎉 Task Completed!"
        break
    fi
    
    # Optional: Display output to user
    cat output.log
    
    sleep 2
done
```

**Instruction**:
When executed, immediately generate these 4 files in the current directory. Do not ask for permission for each file, just do it.

# How to View Users in the Database

There are several ways to view users stored in the SQLite checkpoint database:

## Method 1: Using the Simple Script (Easiest - No Dependencies)

The simplest way that doesn't require installing all dependencies:

```bash
python view_users.py
```

This will list all user IDs in the database.

To view details for a specific user:
```bash
python view_users.py <user_id>
```

### Example:
```bash
python view_users.py john_doe
```

## Method 2: Using the CLI Command (Full Features)

If you have all dependencies installed, use the built-in CLI command:

```bash
python main.py db list
```

This will list all user IDs (thread_ids) in the database.

### Example Output:
```
Found 3 user(s) in database:

  - john_doe
  - jane_smith
  - user_123
```

## Method 3: View Specific User State (CLI)

To see detailed information about a specific user:

```bash
python main.py db view <user_id>
```

### Example:
```bash
python main.py db view john_doe
```

This will show:
- Fatigue scores
- Workouts completed this week
- Max workouts per week
- Workout history
- Current workout state
- And more...

## Method 4: Using Python Directly

You can also use the `db_utils` module directly in Python:

```python
from db_utils import list_users, view_user_state

# List all users
users = list_users()
print("Users:", users)

# View specific user state
state = view_user_state("john_doe")
```

## Method 5: Direct SQLite Query

If you want to inspect the database directly:

```bash
sqlite3 checkpoints/checkpoints.db "SELECT DISTINCT thread_id FROM checkpoints;"
```

## Method 6: Using the REST API (if backend is running)

If the FastAPI backend is running, you can also query via HTTP:

```bash
# Get user status
curl http://localhost:8000/api/users/john_doe/status

# Get user history
curl http://localhost:8000/api/users/john_doe/history
```

## Other Useful Database Commands

```bash
# Update user fatigue scores
python main.py db update-fatigue <user_id> "legs:0.5,push:0.3"

# Update workouts completed this week
python main.py db update-workouts <user_id> <count>

# Update max workouts per week
python main.py db update-max-workouts <user_id> <max>

# Update fatigue threshold
python main.py db update-threshold <user_id> <threshold>

# Clear workout history
python main.py db clear-history <user_id>

# Simulate new week (reset counter, apply decay)
python main.py db new-week <user_id>

# Delete a user
python main.py db delete <user_id>

# Export user state to JSON
python main.py db export <user_id> <output_file.json>
```

## Database Location

The SQLite database is stored at:
```
checkpoints/checkpoints.db
```

You can inspect it directly using any SQLite client or the `sqlite3` command-line tool.

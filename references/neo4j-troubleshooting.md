# Neo4j Troubleshooting Reference

Common errors and fixes when operating Neo4j on macOS (Homebrew).

## Lock File Conflict

### Error
```
java.nio.file.FileSystemNotFoundException
```
or
```
FileLockException: Lock file has been locked by another process: 
/opt/homebrew/var/neo4j/data/databases/store_lock
```

### Root Cause
- Old Neo4j process from a different version still running
- Database lock file held by orphaned process
- Common after `brew upgrade neo4j` without stopping old version first

### Diagnosis
```bash
# Check for running Neo4j processes
ps aux | grep -i neo4j | grep -v grep

# Check which version is running vs installed
brew info neo4j
```

### Solution
```bash
# Kill all Neo4j processes
pkill -f "neo4j"

# Remove lock file
rm -f /opt/homebrew/var/neo4j/data/databases/store_lock

# Start fresh
neo4j start

# Verify
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://localhost:7474
```

### Prevention
Always stop Neo4j before upgrading:
```bash
neo4j stop
brew upgrade neo4j
neo4j start
```

## HTTP 500: FileSystemNotFoundException

### Error
Browser shows:
```
HTTP ERROR 500 java.nio.file.FileSystemNotFoundException
URI: /browser/
```

### Cause
Same root cause as lock file conflict - browser UI cannot load due to database lock.

### Solution
Follow the lock file conflict resolution above.

## Authentication Failures

### Error
```
The client is unauthorized due to authentication failure.
```

### Causes
1. Wrong password
2. Password not changed from default (neo4j/neo4j)
3. Account locked after too many failed attempts

### Solution
1. Access http://localhost:7474 and change password on first login
2. If locked out, reset via:
   ```bash
   # Stop Neo4j
   neo4j stop
   
   # Reset auth (removes all users)
   rm -rf /opt/homebrew/var/neo4j/data/dbms/auth*
   
   # Restart (will accept neo4j/neo4j again)
   neo4j start
   ```

## Port Conflicts

### Check Ports
```bash
lsof -i :7474   # HTTP
lsof -i :7687   # Bolt
```

### Common Conflicts
- Another Neo4j instance
- Other services using same ports

### Solution
Either stop the conflicting service or change Neo4j ports in config:
```bash
# Edit config
nano /opt/homebrew/Cellar/neo4j/$(brew info neo4j --json | jq -r '.[0].installed[0].version')/libexec/conf/neo4j.conf

# Change:
# dbms.connector.http.listen_address=:7474
# dbms.connector.bolt.listen_address=:7687
```

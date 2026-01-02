# Skeleton Fast API App
The intention behind writing this app as to use it a base for further development.

## Configuration
The app reads configuration values from _.env_ file. However, that file will not be shared in the git repository instead an equivalent example file _.env.example_ will be provided.  
### Setting up the .env file
```bash
# In your project root
cp .env.example .env

# Edit with your values
nano .env
```

### Sequence diagram for reading _settings_ with respect to root api **/**
```mermaid
sequenceDiagram
    participant User
    participant FastAPI as API Endpoint
    participant SD as SettingsDep (Dependency)
    participant GS as get_settings()
    participant LRU as LRU Cache
    participant P as Pydantic Settings

    User->>FastAPI: GET /
    FastAPI->>SD: Request Settings
    SD->>GS: Call get_settings()
    
    Note over GS, LRU: Check if Settings already exist in memory
    
    alt Cache Miss (First Call)
        GS->>P: Initialize Settings()
        P->>.env: Read file from disk
        P->>P: Validate & Cast types
        P-->>GS: Settings Object
        GS->>LRU: Store in Cache
    else Cache Hit (Subsequent Calls)
        LRU-->>GS: Return existing Settings Object
    end

    GS-->>SD: Return Settings
    SD-->>FastAPI: Inject Settings into route
    FastAPI-->>User: 200 OK (Response)
```
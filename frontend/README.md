# Plex Watcher Frontend

Streamlit-based web interface for the Plex Watcher service.

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   # Copy the example .env file
   cp .env.example .env
   
   # Edit .env with your settings
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory with the following variables:

```env
# Backend API Configuration
API_ENDPOINT=http://localhost:7799

# Plex Server Configuration (Optional - can be set in UI)
PLEX_SERVER_URL=http://localhost:32400
PLEX_TOKEN=

# Polling Configuration
DEFAULT_POLL_INTERVAL=30

# UI Configuration
AUTO_REFRESH_INTERVAL=5
ENABLE_AUTO_REFRESH=false
```

### Configuration Priority

1. UI form inputs (highest priority)
2. Session state
3. Environment variables
4. Default values (lowest priority)

## Usage

### Starting the Watcher

1. Configure your Plex server URL and authentication token
2. Add paths to watch using the path manager
3. Click "Start Watching" to begin monitoring

### Manual Scanning

Use the "Scan" tab to trigger immediate scans of specific directories without starting the watcher.

### Settings

Access settings in the sidebar to:
- Enable/disable auto-refresh
- Adjust refresh interval
- View current API endpoint

## Architecture

### API Client (`api_client.py`)

- **Async Operations**: Uses `httpx.AsyncClient` for non-blocking requests
- **Caching**: 2-second status cache to reduce backend load
- **Error Handling**: Graceful degradation on connection failures
- **Singleton Pattern**: Single client instance shared across the app

### Components (`components.py`)

Reusable UI components:
- `render_status_indicator()`: Current status display
- `render_configuration_form()`: Plex configuration
- `render_path_manager()`: Path management interface
- `render_watch_controls()`: Start/stop buttons
- `render_scan_form()`: Manual scan interface
- `render_settings_sidebar()`: Application settings

### State Management (`state.py`)

Centralized session state management:
- Configuration persistence
- Backend status caching
- UI settings storage

## Development

### Adding New Features

1. **New API Endpoint**: Add method to `ApiClient` class
2. **New UI Component**: Create function in `components.py`
3. **New State**: Add to `state.py` and initialize in `init_session_state()`
4. **New Config**: Add to `.env.example` and `Config` class

### Best Practices

- Keep components pure and reusable
- Use async for all API calls
- Handle errors gracefully
- Invalidate cache after state-changing operations
- Document configuration options

## Deployment

### Docker

The `.env` file structure is designed for easy Docker deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY frontend/ /app/
RUN pip install -r requirements.txt

ENV API_ENDPOINT=http://backend:7799
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Production Server

For production deployment:

1. Set `ENABLE_AUTO_REFRESH=true` for monitoring dashboards
2. Use reverse proxy (nginx) for HTTPS
3. Configure appropriate `API_ENDPOINT`
4. Secure Plex tokens using secrets management

## Troubleshooting

### Backend Connection Issues

- Verify `API_ENDPOINT` in `.env`
- Check backend server is running on correct port
- Ensure firewall allows connection

### Slow UI

- Disable auto-refresh if not needed
- Increase cache duration in `api_client.py`
- Check network latency to backend

### Configuration Not Saving

- Verify session state initialization
- Check browser console for errors
- Clear browser cache and restart

## License

Apache-2.0

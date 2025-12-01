#!/bin/bash
# =============================================================================
# AEGIS Code Map - Local Development Server
# =============================================================================
# Runs the app locally (without Docker) for full agent support.
# Use this when you need Claude/Codex/Gemini agent functionality.
#
# Usage:
#   ./start-local.sh              # Start backend + frontend dev servers
#   ./start-local.sh --backend    # Start only backend
#   ./start-local.sh --stop       # Stop all servers
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8010
FRONTEND_PORT=5173
BACKEND_PID_FILE="/tmp/aegis-backend.pid"
FRONTEND_PID_FILE="/tmp/aegis-frontend.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if a process is running
is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Stop servers
stop_servers() {
    log_info "Stopping servers..."

    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping backend (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi

    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping frontend (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi

    # Also kill any orphaned processes on the ports
    fuser -k ${BACKEND_PORT}/tcp 2>/dev/null || true
    fuser -k ${FRONTEND_PORT}/tcp 2>/dev/null || true

    log_info "Servers stopped"
}

# Check dependencies
check_dependencies() {
    log_step "Checking dependencies..."

    # Check Python venv
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        log_error "Python venv not found. Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi

    # Check node_modules
    if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        log_warn "Frontend dependencies not installed. Installing..."
        cd "$SCRIPT_DIR/frontend"
        npm install
        cd "$SCRIPT_DIR"
    fi

    # Check if CLI agents are available
    log_step "Checking agent CLIs..."
    local agents_found=""

    if command -v claude &> /dev/null; then
        agents_found="${agents_found}Claude "
    fi
    if command -v codex &> /dev/null; then
        agents_found="${agents_found}Codex "
    fi
    if command -v gemini &> /dev/null; then
        agents_found="${agents_found}Gemini "
    fi

    if [ -n "$agents_found" ]; then
        log_info "Available agents: $agents_found"
    else
        log_warn "No agent CLIs found in PATH. Agent features will not work."
        log_warn "Install at least one: claude, codex, or gemini"
    fi
}

# Start backend
start_backend() {
    if is_running "$BACKEND_PID_FILE"; then
        log_info "Backend already running"
        return 0
    fi

    log_step "Starting backend on port $BACKEND_PORT..."

    cd "$SCRIPT_DIR"
    source .venv/bin/activate

    # Start uvicorn in background
    CODE_MAP_ROOT="${CODE_MAP_ROOT:-$HOME}" \
    nohup .venv/bin/uvicorn code_map.server:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        > /tmp/aegis-backend.log 2>&1 &

    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"

    # Wait for backend to be ready
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if curl -s -f "http://localhost:$BACKEND_PORT/api/settings" > /dev/null 2>&1; then
            log_info "Backend started (PID: $pid)"
            return 0
        fi
        sleep 1
        ((attempts++))
    done

    log_error "Backend failed to start. Check /tmp/aegis-backend.log"
    return 1
}

# Start frontend
start_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        log_info "Frontend already running"
        return 0
    fi

    log_step "Starting frontend on port $FRONTEND_PORT..."

    cd "$SCRIPT_DIR/frontend"

    # Start Vite dev server in background
    VITE_DEPLOY_BACKEND_URL="http://localhost:$BACKEND_PORT" \
    nohup npm run dev -- --port $FRONTEND_PORT --host \
        > /tmp/aegis-frontend.log 2>&1 &

    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"

    # Wait for frontend to be ready
    sleep 3

    if is_running "$FRONTEND_PID_FILE"; then
        log_info "Frontend started (PID: $pid)"
        return 0
    else
        log_error "Frontend failed to start. Check /tmp/aegis-frontend.log"
        return 1
    fi
}

# Find available browser
find_browser() {
    if command -v chromium-browser &> /dev/null; then
        echo "chromium-browser"
    elif command -v chromium &> /dev/null; then
        echo "chromium"
    elif command -v google-chrome &> /dev/null; then
        echo "google-chrome"
    elif command -v google-chrome-stable &> /dev/null; then
        echo "google-chrome-stable"
    elif command -v firefox &> /dev/null; then
        echo "firefox"
    else
        echo ""
    fi
}

# Launch browser
launch_browser() {
    local url="http://localhost:$FRONTEND_PORT"
    local browser=$(find_browser)

    if [ -z "$browser" ]; then
        log_warn "No browser found. Open $url manually."
        return
    fi

    log_info "Opening $url in $browser..."

    case "$browser" in
        chromium-browser|chromium|google-chrome|google-chrome-stable)
            "$browser" --app="$url" --window-size=1400,900 &
            ;;
        firefox)
            "$browser" "$url" &
            ;;
    esac
}

# Show status
show_status() {
    echo ""
    echo "==================================="
    echo "  AEGIS Code Map - Local Mode"
    echo "==================================="

    if is_running "$BACKEND_PID_FILE"; then
        echo -e "Backend:  ${GREEN}Running${NC} (http://localhost:$BACKEND_PORT)"
    else
        echo -e "Backend:  ${RED}Stopped${NC}"
    fi

    if is_running "$FRONTEND_PID_FILE"; then
        echo -e "Frontend: ${GREEN}Running${NC} (http://localhost:$FRONTEND_PORT)"
    else
        echo -e "Frontend: ${RED}Stopped${NC}"
    fi

    echo ""
    echo "Logs:"
    echo "  Backend:  /tmp/aegis-backend.log"
    echo "  Frontend: /tmp/aegis-frontend.log"
    echo ""
    echo "Stop with: $0 --stop"
    echo "==================================="
}

# Main
main() {
    case "${1:-}" in
        --stop)
            stop_servers
            exit 0
            ;;
        --backend)
            check_dependencies
            start_backend
            show_status
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [--backend|--stop|--status|--help]"
            echo ""
            echo "Runs AEGIS locally (not in Docker) for full agent support."
            echo ""
            echo "Options:"
            echo "  (none)     Start backend + frontend, open browser"
            echo "  --backend  Start only the backend server"
            echo "  --stop     Stop all servers"
            echo "  --status   Show server status"
            echo "  --help     Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  CODE_MAP_ROOT  Project root path (default: \$HOME)"
            exit 0
            ;;
        "")
            # Default: start everything
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac

    check_dependencies
    start_backend
    start_frontend
    show_status
    sleep 2
    launch_browser
}

main "$@"

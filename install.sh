#!/bin/bash

################################################################################
# TRIAS API Server - Comprehensive Installation Script
# 
# This script handles:
# - Dependency installation
# - System configuration
# - Service setup and management
# - Updates and maintenance
# - Error handling and recovery
#
# Usage: sudo bash install.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="trias"
APP_USER="trias"
APP_GROUP="trias"
INSTALL_DIR="/opt/trias"
SERVICE_NAME="trias.service"
LOG_DIR="/var/log/trias"
RUN_DIR="/var/run/trias"
PYTHON_VERSION="3.9"

# Git repository (will be auto-detected or can be set manually)
GIT_REPO=""
DEFAULT_GIT_REPO="https://github.com/angeeinstein/trias.git"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
    print_success "Running as root"
}

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        print_success "Detected OS: $OS $VERSION"
    else
        print_error "Cannot detect OS"
        exit 1
    fi
}

# Check if service exists
service_exists() {
    systemctl list-unit-files | grep -q "^${SERVICE_NAME}"
    return $?
}

# Check if installation exists
installation_exists() {
    [ -d "$INSTALL_DIR" ]
    return $?
}

# Detect git repository URL
detect_git_repo() {
    if [ -d "$SCRIPT_DIR/.git" ]; then
        GIT_REPO=$(cd "$SCRIPT_DIR" && git config --get remote.origin.url 2>/dev/null || echo "")
        if [ -n "$GIT_REPO" ]; then
            print_success "Detected git repository: $GIT_REPO"
            return 0
        fi
    fi
    return 1
}

# Prompt for git repository
prompt_git_repo() {
    echo ""
    print_info "No git repository detected."
    echo "You can either:"
    echo "  1) Use default repository: $DEFAULT_GIT_REPO"
    echo "  2) Provide a different git repository URL"
    echo "  3) Use local files (no git updates available)"
    echo ""
    read -p "Enter git repository URL (or press Enter for default): " user_repo
    
    if [ -z "$user_repo" ]; then
        GIT_REPO="$DEFAULT_GIT_REPO"
        print_success "Using default repository: $GIT_REPO"
        return 0
    elif [ "$user_repo" = "local" ] || [ "$user_repo" = "skip" ]; then
        print_info "Will use local files"
        return 1
    else
        GIT_REPO="$user_repo"
        print_success "Will use git repository: $GIT_REPO"
        return 0
    fi
}

################################################################################
# Installation Menu
################################################################################

show_menu() {
    clear
    print_header "TRIAS API Server Installation"
    echo ""
    
    if installation_exists; then
        print_warning "Existing installation detected at $INSTALL_DIR"
        echo ""
        echo "1) Update existing installation"
        echo "2) Reinstall (remove and install fresh)"
        echo "3) Uninstall"
        echo "4) View service status"
        echo "5) View logs"
        echo "6) Restart service"
        echo "7) Exit"
        echo ""
        read -p "Choose an option [1-7]: " choice
        
        case $choice in
            1) update_installation ;;
            2) reinstall ;;
            3) uninstall ;;
            4) show_status ;;
            5) show_logs ;;
            6) restart_service ;;
            7) exit 0 ;;
            *) print_error "Invalid option"; sleep 2; show_menu ;;
        esac
    else
        print_info "No existing installation found"
        echo ""
        echo "1) Install TRIAS API Server"
        echo "2) Exit"
        echo ""
        read -p "Choose an option [1-2]: " choice
        
        case $choice in
            1) fresh_install ;;
            2) exit 0 ;;
            *) print_error "Invalid option"; sleep 2; show_menu ;;
        esac
    fi
}

################################################################################
# Package Installation
################################################################################

install_packages() {
    print_header "Installing System Packages"
    
    case $OS in
        ubuntu|debian)
            print_info "Updating package lists..."
            apt-get update -qq
            
            print_info "Installing required packages..."
            DEBIAN_FRONTEND=noninteractive apt-get install -y \
                python3 \
                python3-pip \
                python3-venv \
                python3-dev \
                build-essential \
                curl \
                git \
                || {
                    print_error "Failed to install packages"
                    exit 1
                }
            ;;
            
        centos|rhel|fedora)
            print_info "Installing required packages..."
            if command -v dnf &> /dev/null; then
                dnf install -y \
                    python3 \
                    python3-pip \
                    python3-devel \
                    gcc \
                    curl \
                    git \
                    || {
                        print_error "Failed to install packages"
                        exit 1
                    }
            else
                yum install -y \
                    python3 \
                    python3-pip \
                    python3-devel \
                    gcc \
                    curl \
                    git \
                    || {
                        print_error "Failed to install packages"
                        exit 1
                    }
            fi
            ;;
            
        *)
            print_warning "Unsupported OS: $OS"
            print_info "Attempting to continue with existing Python installation..."
            ;;
    esac
    
    # Verify Python installation
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed and could not be installed automatically"
        exit 1
    fi
    
    PYTHON_VERSION_INSTALLED=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION_INSTALLED installed"
    
    # Verify git installation
    if ! command -v git &> /dev/null; then
        print_warning "Git is not installed. Updates via git pull will not be available."
    else
        GIT_VERSION=$(git --version | cut -d' ' -f3)
        print_success "Git $GIT_VERSION installed"
    fi
}

################################################################################
# User and Directory Setup
################################################################################

setup_user() {
    print_header "Setting Up Application User"
    
    # Create user if doesn't exist
    if ! id "$APP_USER" &>/dev/null; then
        print_info "Creating user $APP_USER..."
        useradd -r -s /bin/bash -d "$INSTALL_DIR" "$APP_USER" || {
            print_error "Failed to create user"
            exit 1
        }
        print_success "User $APP_USER created"
    else
        print_info "User $APP_USER already exists"
    fi
}

setup_directories() {
    print_header "Setting Up Directories"
    
    # Create install directory
    print_info "Creating $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    
    # Create log directory
    print_info "Creating $LOG_DIR..."
    mkdir -p "$LOG_DIR"
    
    # Create run directory
    print_info "Creating $RUN_DIR..."
    mkdir -p "$RUN_DIR"
    
    print_success "Directories created"
}

################################################################################
# Application Installation
################################################################################

install_application() {
    print_header "Installing Application"
    
    # Get application files
    if [ -n "$GIT_REPO" ]; then
        # Clone from git repository
        print_info "Cloning from git repository..."
        print_info "Repository: $GIT_REPO"
        
        git clone "$GIT_REPO" "$INSTALL_DIR" || {
            print_error "Failed to clone repository"
            print_info "Falling back to local file copy..."
            mkdir -p "$INSTALL_DIR"
            cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" || {
                print_error "Failed to copy files"
                exit 1
            }
        }
        
        if [ -d "$INSTALL_DIR/.git" ]; then
            print_success "Repository cloned successfully"
        else
            print_warning "Using local files (no git repository)"
        fi
    else
        # Copy local files
        print_info "Copying application files from local directory..."
        mkdir -p "$INSTALL_DIR"
        cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" || {
            print_error "Failed to copy files"
            exit 1
        }
        print_success "Files copied"
    fi
    
    # Remove install script from installation directory
    rm -f "$INSTALL_DIR/install.sh"
    
    # Create virtual environment
    print_info "Creating Python virtual environment..."
    cd "$INSTALL_DIR"
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment exists, removing..."
        rm -rf venv
    fi
    
    python3 -m venv venv || {
        print_error "Failed to create virtual environment"
        exit 1
    }
    
    print_success "Virtual environment created"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    ./venv/bin/pip install --upgrade pip setuptools wheel -q
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    ./venv/bin/pip install -r requirements.txt -q || {
        print_error "Failed to install Python dependencies"
        exit 1
    }
    
    print_success "Dependencies installed"
}

################################################################################
# Service Configuration
################################################################################

setup_service() {
    print_header "Setting Up Systemd Service"
    
    # Copy service file
    print_info "Installing service file..."
    cp "$INSTALL_DIR/$SERVICE_NAME" /etc/systemd/system/ || {
        print_error "Failed to copy service file"
        exit 1
    }
    
    # Reload systemd
    print_info "Reloading systemd..."
    systemctl daemon-reload
    
    # Enable service
    print_info "Enabling service..."
    systemctl enable "$SERVICE_NAME" || {
        print_error "Failed to enable service"
        exit 1
    }
    
    print_success "Service configured"
}

################################################################################
# Permissions
################################################################################

set_permissions() {
    print_header "Setting Permissions"
    
    # Set ownership
    print_info "Setting ownership..."
    chown -R "$APP_USER:$APP_GROUP" "$INSTALL_DIR"
    chown -R "$APP_USER:$APP_GROUP" "$LOG_DIR"
    chown -R "$APP_USER:$APP_GROUP" "$RUN_DIR"
    
    # Set permissions
    print_info "Setting permissions..."
    chmod -R 755 "$INSTALL_DIR"
    chmod -R 755 "$LOG_DIR"
    chmod -R 755 "$RUN_DIR"
    
    print_success "Permissions set"
}

################################################################################
# Firewall Configuration
################################################################################

configure_firewall() {
    print_header "Configuring Firewall"
    
    # Determine which port to open (80 or 8080)
    if grep -q "USE_PORT_80=true" "$INSTALL_DIR/trias.service" 2>/dev/null; then
        FIREWALL_PORT=80
    else
        FIREWALL_PORT=8080
    fi
    
    print_info "Opening port $FIREWALL_PORT for the application..."
    
    # Check if firewall is active
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        print_info "Configuring UFW firewall..."
        ufw allow ${FIREWALL_PORT}/tcp comment "TRIAS API Server" || print_warning "Failed to configure UFW"
        print_success "UFW configured for port $FIREWALL_PORT"
        
    elif command -v firewall-cmd &> /dev/null && systemctl is-active firewalld &> /dev/null; then
        print_info "Configuring firewalld..."
        firewall-cmd --permanent --add-port=${FIREWALL_PORT}/tcp || print_warning "Failed to configure firewalld"
        firewall-cmd --reload || print_warning "Failed to reload firewalld"
        print_success "Firewalld configured for port $FIREWALL_PORT"
        
    else
        print_warning "No supported firewall detected or firewall not active"
        print_info "Port $FIREWALL_PORT may need to be opened manually"
    fi
}

################################################################################
# Service Management
################################################################################

start_service() {
    print_header "Starting Service"
    
    systemctl start "$SERVICE_NAME" || {
        print_error "Failed to start service"
        print_info "Check logs with: journalctl -u $SERVICE_NAME -n 50"
        return 1
    }
    
    # Wait a moment for service to start
    sleep 2
    
    # Check if service is running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully"
        return 0
    else
        print_error "Service failed to start"
        print_info "Check logs with: journalctl -u $SERVICE_NAME -n 50"
        return 1
    fi
}

restart_service() {
    print_header "Restarting Service"
    
    systemctl restart "$SERVICE_NAME" || {
        print_error "Failed to restart service"
        return 1
    }
    
    sleep 2
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service restarted successfully"
    else
        print_error "Service failed to restart"
    fi
    
    read -p "Press Enter to continue..."
    show_menu
}

stop_service() {
    print_header "Stopping Service"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME" || {
            print_error "Failed to stop service"
            return 1
        }
        print_success "Service stopped"
    else
        print_info "Service is not running"
    fi
}

show_status() {
    clear
    print_header "Service Status"
    echo ""
    systemctl status "$SERVICE_NAME" --no-pager || true
    echo ""
    
    # Detect which port is being used
    if grep -q "USE_PORT_80=true" "$INSTALL_DIR/trias.service" 2>/dev/null || \
       grep -q 'Environment="USE_PORT_80=true"' /etc/systemd/system/"$SERVICE_NAME" 2>/dev/null; then
        TEST_PORT=80
    else
        TEST_PORT=8080
    fi
    
    # Test HTTP connection
    print_info "Testing HTTP connection on port $TEST_PORT..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:${TEST_PORT}/ | grep -q "200"; then
        print_success "Server is responding on port $TEST_PORT"
    else
        print_warning "Server is not responding on port $TEST_PORT"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

show_logs() {
    clear
    print_header "Recent Logs"
    echo ""
    echo "=== Systemd Journal Logs ==="
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true
    echo ""
    echo "=== Error Log ==="
    if [ -f "$LOG_DIR/error.log" ]; then
        tail -n 20 "$LOG_DIR/error.log" || true
    else
        print_info "No error log found"
    fi
    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

################################################################################
# Installation Workflows
################################################################################

fresh_install() {
    clear
    print_header "Fresh Installation"
    
    # Check prerequisites
    check_root
    detect_os
    
    # Detect or prompt for git repository
    if ! detect_git_repo; then
        prompt_git_repo
    fi
    
    # Install components
    install_packages
    setup_user
    setup_directories
    install_application
    setup_service
    set_permissions
    configure_firewall
    
    # Start service
    if start_service; then
        echo ""
        print_success "Installation completed successfully!"
        echo ""
        print_info "Service Status: $(systemctl is-active $SERVICE_NAME)"
        
        # Detect which port is configured
        if grep -q 'USE_PORT_80=true' /etc/systemd/system/"$SERVICE_NAME" 2>/dev/null; then
            SERVER_PORT=80
        else
            SERVER_PORT=8080
        fi
        
        print_info "Access the web interface at: http://$(hostname -I | awk '{print $1}'):$SERVER_PORT"
        print_info "Or locally at: http://localhost:$SERVER_PORT"
        echo ""
        print_info "Note: Server is running on port $SERVER_PORT"
        if [ "$SERVER_PORT" = "8080" ]; then
            echo "  To use port 80, edit /etc/systemd/system/$SERVICE_NAME:"
            echo "  1. Change: Environment=\"USE_PORT_80=false\" to Environment=\"USE_PORT_80=true\""
            echo "  2. Uncomment: AmbientCapabilities=CAP_NET_BIND_SERVICE"
            echo "  3. Run: sudo systemctl daemon-reload && sudo systemctl restart $SERVICE_NAME"
        fi
        echo ""
        print_info "Useful commands:"
        echo "  - View status:  sudo systemctl status $SERVICE_NAME"
        echo "  - View logs:    sudo journalctl -u $SERVICE_NAME -f"
        echo "  - Restart:      sudo systemctl restart $SERVICE_NAME"
        echo "  - Stop:         sudo systemctl stop $SERVICE_NAME"
        echo ""
    else
        print_error "Installation completed but service failed to start"
        print_info "Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
    fi
    
    read -p "Press Enter to return to menu..."
    show_menu
}

update_installation() {
    clear
    print_header "Updating Installation"
    
    # Stop service
    stop_service
    
    # Backup current installation
    print_info "Creating backup..."
    BACKUP_DIR="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r "$INSTALL_DIR" "$BACKUP_DIR" || print_warning "Backup failed"
    
    # Update files
    cd "$INSTALL_DIR"
    
    if [ -d ".git" ]; then
        # Update from git repository
        print_info "Pulling latest changes from git repository..."
        
        # Get current branch
        CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
        print_info "Current branch: $CURRENT_BRANCH"
        
        # Stash any local changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            print_warning "Local changes detected, stashing..."
            git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)" || print_warning "Failed to stash changes"
        fi
        
        # Pull latest changes
        git pull origin "$CURRENT_BRANCH" || {
            print_error "Failed to pull from repository"
            print_warning "Restoring from backup..."
            cd /
            rm -rf "$INSTALL_DIR"
            mv "$BACKUP_DIR" "$INSTALL_DIR"
            read -p "Press Enter to return to menu..."
            show_menu
            return 1
        }
        
        print_success "Git repository updated successfully"
    else
        # Update from local files (no git)
        print_info "No git repository found, updating from local files..."
        
        if [ ! -d "$SCRIPT_DIR" ] || [ "$SCRIPT_DIR" = "$INSTALL_DIR" ]; then
            print_warning "Cannot update: no source directory available"
            print_info "To enable git-based updates, run: cd $INSTALL_DIR && git init && git remote add origin <your-repo-url>"
            rm -rf "$BACKUP_DIR"
            read -p "Press Enter to return to menu..."
            show_menu
            return 1
        fi
        
        # Copy new files (excluding venv and .git)
        for item in "$SCRIPT_DIR"/*; do
            item_name=$(basename "$item")
            if [ "$item_name" != "venv" ] && [ "$item_name" != "install.sh" ] && [ "$item_name" != ".git" ]; then
                cp -r "$item" "$INSTALL_DIR/" || print_warning "Failed to copy $item_name"
            fi
        done
        
        print_success "Files updated from local directory"
    fi
    
    # Update dependencies
    print_info "Updating Python dependencies..."
    ./venv/bin/pip install -r requirements.txt --upgrade -q || {
        print_error "Failed to update dependencies"
        print_warning "Restoring from backup..."
        cd /
        rm -rf "$INSTALL_DIR"
        mv "$BACKUP_DIR" "$INSTALL_DIR"
        read -p "Press Enter to return to menu..."
        show_menu
        return 1
    }
    
    # Update service file
    print_info "Updating service configuration..."
    cp "$INSTALL_DIR/$SERVICE_NAME" /etc/systemd/system/
    systemctl daemon-reload
    
    # Set permissions
    set_permissions
    
    # Start service
    if start_service; then
        echo ""
        print_success "Update completed successfully!"
        print_info "Backup kept at: $BACKUP_DIR"
        
        if [ -d "$INSTALL_DIR/.git" ]; then
            CURRENT_COMMIT=$(cd "$INSTALL_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            print_info "Current commit: $CURRENT_COMMIT"
        fi
    else
        print_error "Update completed but service failed to start"
    fi
    
    read -p "Press Enter to return to menu..."
    show_menu
}

reinstall() {
    clear
    print_header "Reinstalling"
    
    print_warning "This will remove the existing installation and install fresh"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_info "Reinstall cancelled"
        sleep 2
        show_menu
        return
    fi
    
    # Uninstall
    uninstall_silent
    
    # Fresh install
    fresh_install
}

uninstall_silent() {
    # Stop and disable service
    if service_exists; then
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "/etc/systemd/system/$SERVICE_NAME"
        systemctl daemon-reload
    fi
    
    # Remove files
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"
    fi
    
    if [ -d "$RUN_DIR" ]; then
        rm -rf "$RUN_DIR"
    fi
}

uninstall() {
    clear
    print_header "Uninstalling TRIAS API Server"
    
    print_warning "This will remove all files and configurations"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_info "Uninstall cancelled"
        sleep 2
        show_menu
        return
    fi
    
    uninstall_silent
    
    # Optionally remove user
    read -p "Remove user $APP_USER? (yes/no): " remove_user
    if [ "$remove_user" = "yes" ]; then
        if id "$APP_USER" &>/dev/null; then
            userdel "$APP_USER" 2>/dev/null || print_warning "Failed to remove user"
            print_success "User removed"
        fi
    fi
    
    print_success "Uninstall completed"
    echo ""
    read -p "Press Enter to exit..."
    exit 0
}

################################################################################
# Main
################################################################################

main() {
    # Initial checks
    check_root
    detect_os
    
    # Show menu
    show_menu
}

# Run main function
main

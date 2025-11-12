#!/bin/bash

# CodeNews Deployment Script
# This script helps with manual deployment

set -e

echo "🚀 CodeNews Deployment Script"
echo "=============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Function to build and start
build_and_start() {
    echo -e "${YELLOW}📦 Building Docker image...${NC}"
    docker-compose build
    
    echo -e "${YELLOW}🚀 Starting containers...${NC}"
    docker-compose up -d
    
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "Container status:"
    docker-compose ps
    
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
}

# Function to stop
stop_containers() {
    echo -e "${YELLOW}🛑 Stopping containers...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Containers stopped${NC}"
}

# Function to view logs
view_logs() {
    docker-compose logs -f
}

# Function to restart
restart_containers() {
    echo -e "${YELLOW}🔄 Restarting containers...${NC}"
    docker-compose restart
    echo -e "${GREEN}✅ Containers restarted${NC}"
}

# Function to clean
clean_all() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker-compose down -v
    docker system prune -f
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Main menu
case "${1:-start}" in
    start)
        build_and_start
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_containers
        ;;
    logs)
        view_logs
        ;;
    clean)
        clean_all
        ;;
    *)
        echo "Usage: ./deploy.sh {start|stop|restart|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  start   - Build and start containers (default)"
        echo "  stop    - Stop containers"
        echo "  restart - Restart containers"
        echo "  logs    - View container logs"
        echo "  clean   - Stop containers and clean up"
        exit 1
        ;;
esac

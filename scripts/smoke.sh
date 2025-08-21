#!/bin/bash
set -e

echo "🚀 Starting smoke test for Mini Chat..."

# Default values
PORT=${PORT:-8000}
HOST=${HOST:-localhost}
MAX_WAIT=${MAX_WAIT:-30}
WAIT_INTERVAL=${WAIT_INTERVAL:-1}

echo "📍 Testing against http://$HOST:$PORT"

# Function to check if port is listening
wait_for_port() {
    echo "⏳ Waiting for app to start on port $PORT..."
    local waited=0
    
    while [ $waited -lt $MAX_WAIT ]; do
        if curl -s "http://$HOST:$PORT/health" > /dev/null 2>&1; then
            echo "✅ App is responding on port $PORT"
            return 0
        fi
        
        echo "   Still waiting... ($waited/$MAX_WAIT seconds)"
        sleep $WAIT_INTERVAL
        waited=$((waited + WAIT_INTERVAL))
    done
    
    echo "❌ Timeout waiting for app to start"
    return 1
}

# Function to run health check
test_health() {
    echo "🏥 Testing health endpoint..."
    local response=$(curl -s "http://$HOST:$PORT/health")
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        echo "✅ Health check passed"
        echo "📊 Response: $response"
        return 0
    else
        echo "❌ Health check failed"
        echo "📊 Response: $response"
        return 1
    fi
}

# Function to test happy path
test_happy_path() {
    echo "🎯 Testing happy path..."
    
    # Test the root endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/")
    
    if [ "$response" = "200" ]; then
        echo "✅ Root endpoint returns 200"
        return 0
    else
        echo "❌ Root endpoint returned $response"
        return 1
    fi
}

# Main test execution
main() {
    echo "🔍 Starting smoke test..."
    
    # Wait for app to be ready
    if ! wait_for_port; then
        echo "❌ Smoke test failed: App did not start"
        exit 1
    fi
    
    # Test health endpoint
    if ! test_health; then
        echo "❌ Smoke test failed: Health check failed"
        exit 1
    fi
    
    # Test happy path
    if ! test_happy_path; then
        echo "❌ Smoke test failed: Happy path test failed"
        exit 1
    fi
    
    echo "🎉 SMOKE TEST PASSED!"
    echo "✅ App is running and responding correctly"
}

# Run the test
main "$@"

#!/bin/bash
# Quick backend validation script

echo "=============================="
echo "🚀 Quick Backend Test"
echo "=============================="
echo

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s --max-time 2 http://localhost:8000/api/health)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "   ✅ Health check passed"
    echo "   Response: $HEALTH"
else
    echo "   ❌ Health check failed"
    exit 1
fi
echo

# Test 2: Chat endpoint (just check it starts streaming)
echo "2️⃣  Testing chat endpoint (simple message)..."
echo "   Sending: 'Hello'"
RESPONSE=$(timeout 10 curl -s -N -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello"}' | head -30)

if echo "$RESPONSE" | grep -q "event:"; then
    echo "   ✅ Chat endpoint responding with SSE events"
    echo "   First few events:"
    echo "$RESPONSE" | head -15 | sed 's/^/   /'
else
    echo "   ❌ Chat endpoint not responding properly"
    echo "   Response: $RESPONSE"
    exit 1
fi
echo

echo "=============================="
echo "✅ Backend is working!"
echo "=============================="
echo
echo "⚠️  IMPORTANT: Access frontend at http://localhost:3000"
echo "   NOT at devtunnels URL (https://...)use.devtunnels.ms)"
echo
echo "Test prompts:"
echo "  • 'What are customers saying about Jira integration?'"
echo "  • 'Calculate our team velocity'"
echo "  • 'RICE score this feature: reach=1000, impact=3, confidence=80%, effort=2 weeks'"
echo

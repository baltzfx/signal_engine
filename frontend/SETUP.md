# Next.js Chat UI Setup Guide

## Prerequisites

- Node.js 18+ installed
- SignalEngine backend running on port 8000

## Installation

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install
```

## Configuration

The app is pre-configured to connect to `localhost:8000`. If your backend is on a different host, create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://your-backend:8000
NEXT_PUBLIC_WS_URL=ws://your-backend:8000/ws/feed
```

## Running

```bash
# Development mode (with hot reload)
npm run dev

# Production build
npm run build
npm start
```

Open [http://localhost:3000](http://localhost:3000)

## Features Explained

### Real-Time Signal Notifications
- Signals appear as beautiful cards in the chat
- Shows direction (LONG/SHORT), confidence score, price levels
- MTF alignment badges for multi-timeframe confirmation
- Trigger events display

### AI Chat Interface
- Type any question about the market
- Ask for analysis, trends, top symbols
- Natural language queries powered by Ollama

### Performance Sidebar
- Live signal statistics
- System metrics (CPU, memory, uptime)
- Quick action buttons
- Collapsible design

## Quick Actions

Try these questions:
- "What's the market trend?"
- "Show me top performing symbols"
- "Any strong signals right now?"
- "Explain the latest BTCUSDT signal"

## Troubleshooting

### WebSocket Not Connecting
1. Ensure backend is running: `python -m app`
2. Check Redis is running: `docker-compose up redis`
3. Verify WebSocket endpoint: `ws://localhost:8000/ws/feed`

### API Errors
1. Check backend health: `http://localhost:8000/health`
2. Verify CORS settings allow `localhost:3000`
3. Check browser console for errors

### Build Issues
```bash
# Clear cache and rebuild
rm -rf .next node_modules
npm install
npm run dev
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Next.js Frontend (3000)         │
│  ┌─────────────────────────────────┐   │
│  │  Chat UI Components             │   │
│  │  - ChatContainer                │   │
│  │  - SignalCard                   │   │
│  │  - ChatInput                    │   │
│  │  - Sidebar                      │   │
│  └─────────────────────────────────┘   │
│               ↕                         │
│  ┌─────────────────────────────────┐   │
│  │  Context & State Management     │   │
│  │  - SignalContext                │   │
│  │  - useWebSocket hook            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                ↕ WebSocket & REST
┌─────────────────────────────────────────┐
│      FastAPI Backend (8000)             │
│  - /ws/feed (WebSocket)                 │
│  - /query/custom (AI queries)           │
│  - /signals (Recent signals)            │
│  - /performance/stats (Metrics)         │
└─────────────────────────────────────────┘
```

## Technology Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Beautiful icons
- **WebSocket API**: Real-time communication

## Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables for Production
```env
NEXT_PUBLIC_API_URL=https://your-api.com
NEXT_PUBLIC_WS_URL=wss://your-api.com/ws/feed
```

## Next Steps

1. Start the backend: `python -m app`
2. Start the frontend: `npm run dev`
3. Open `http://localhost:3000`
4. Watch real-time signals appear in the chat!

## Customization

### Change Theme Colors
Edit [tailwind.config.ts](./tailwind.config.ts):
```typescript
colors: {
  primary: {
    500: '#your-color',
    // ...
  }
}
```

### Modify Signal Display
Edit [src/components/SignalCard.tsx](./src/components/SignalCard.tsx)

### Add Custom Quick Actions
Edit [src/components/Sidebar.tsx](./src/components/Sidebar.tsx)

## Support

For issues or questions:
1. Check the main README.md
2. Review backend logs
3. Check browser console
4. Verify all services are running (Redis, Backend, Frontend)

# SignalEngine Frontend - Next.js Chat UI

Modern chat-like interface for SignalEngine v3 with real-time signal notifications and AI-powered market analysis.

## Features

- 🔴 **Real-Time WebSocket**: Live signal streaming
- 💬 **Chat Interface**: Natural conversation with AI
- 📊 **Signal Cards**: Beautiful signal notifications
- 📈 **Performance Metrics**: Live stats in sidebar
- 📱 **Responsive Design**: Works on all devices
- 🎨 **Modern UI**: Tailwind CSS with gradient themes

## Quick Start

```bash
# Install dependencies
npm install

# Set environment variables (optional)
cp .env.example .env.local

# Run development server
npm run dev

# Open http://localhost:3000
```

## Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/feed
```

## Development

```bash
# Development
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint
npm run lint
```

## Architecture

```
src/
├── app/                    # Next.js App Router
│   ├── page.tsx           # Main chat page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ChatContainer.tsx  # Main chat area
│   ├── ChatMessage.tsx    # Message bubble
│   ├── ChatInput.tsx      # User input
│   ├── SignalCard.tsx     # Signal notification
│   └── Sidebar.tsx        # Stats sidebar
├── contexts/              # React contexts
│   └── SignalContext.tsx  # Global signal state
├── hooks/                 # Custom hooks
│   └── useWebSocket.ts    # WebSocket connection
├── lib/                   # Utilities
│   └── api.ts            # API client
└── types/                 # TypeScript types
    └── index.ts          # Type definitions
```

## Key Components

### ChatContainer
Main chat interface that displays messages and handles user input.

### SignalCard
Beautiful card component for displaying trading signals with:
- Direction indicators (long/short)
- Price levels (entry, TP, SL)
- MTF alignment badges
- Trigger events
- Confidence scores

### Sidebar
Collapsible sidebar showing:
- Connection status
- Signal statistics
- System metrics
- Quick action buttons

### useWebSocket Hook
Manages WebSocket connection with:
- Auto-reconnect
- Message handling
- Connection status

## Integration with Backend

The frontend connects to the FastAPI backend:

- **WebSocket**: `ws://localhost:8000/ws/feed` for real-time signals
- **REST API**: `http://localhost:8000/` for queries and data

### API Endpoints Used

- `GET /query/custom?query=...` - AI queries
- `GET /query/top-symbols?count=5` - Top symbols
- `GET /signals?limit=50` - Recent signals
- `GET /performance/stats?lookback_days=7` - Performance stats
- `GET /health` - Health check

## Customization

### Colors
Edit `tailwind.config.ts` to change theme colors.

### Chat Behavior
Modify `src/contexts/SignalContext.tsx` to customize message handling.

### Signal Display
Update `src/components/SignalCard.tsx` for different signal layouts.

## Production Deployment

```bash
# Build
npm run build

# The output is in .next/ directory
# Deploy to Vercel, Netlify, or any Node.js host
```

### Vercel Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Troubleshooting

**WebSocket not connecting:**
- Check backend is running on port 8000
- Verify `NEXT_PUBLIC_WS_URL` is correct
- Check browser console for errors

**API requests failing:**
- Ensure backend is running
- Check CORS settings in backend
- Verify `NEXT_PUBLIC_API_URL` is correct

**Build errors:**
- Clear `.next` folder: `rm -rf .next`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

## License

Same as parent project (SignalEngine v3)

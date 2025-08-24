import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from 'react-query';

import Layout from './components/Layout';
import LiveFeed from './pages/LiveFeed';
import Alerts from './pages/Alerts';
import Simulator from './pages/Simulator';
import Dashboard from './pages/Dashboard';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#0a0a0a',
      paper: '#1a1a1a',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live-feed" element={<LiveFeed />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/simulator" element={<Simulator />} />
            </Routes>
          </Layout>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;

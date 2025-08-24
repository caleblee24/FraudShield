import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp,
  Warning,
  Speed,
  CheckCircle,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard: React.FC = () => {
  // Mock data - in real app this would come from API
  const metrics = {
    totalTransactions: 15420,
    alertsGenerated: 342,
    avgLatency: 45,
    accuracy: 94.2,
  };

  const chartData = [
    { time: '00:00', transactions: 120, alerts: 8 },
    { time: '04:00', transactions: 85, alerts: 5 },
    { time: '08:00', transactions: 200, alerts: 12 },
    { time: '12:00', transactions: 350, alerts: 18 },
    { time: '16:00', transactions: 280, alerts: 15 },
    { time: '20:00', transactions: 180, alerts: 10 },
  ];

  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ReactNode;
    color: string;
    subtitle?: string;
  }> = ({ title, value, icon, color, subtitle }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="h6">
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="textSecondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              backgroundColor: color,
              borderRadius: '50%',
              p: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Metrics Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Transactions"
            value={metrics.totalTransactions.toLocaleString()}
            icon={<TrendingUp sx={{ color: 'white' }} />}
            color="#2196f3"
            subtitle="Last 24 hours"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Alerts Generated"
            value={metrics.alertsGenerated}
            icon={<Warning sx={{ color: 'white' }} />}
            color="#f50057"
            subtitle="Suspicious transactions"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Latency"
            value={`${metrics.avgLatency}ms`}
            icon={<Speed sx={{ color: 'white' }} />}
            color="#4caf50"
            subtitle="P95 response time"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Accuracy"
            value={`${metrics.accuracy}%`}
            icon={<CheckCircle sx={{ color: 'white' }} />}
            color="#ff9800"
            subtitle="Fraud detection rate"
          />
        </Grid>

        {/* Charts */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Transaction Volume & Alerts (24h)
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="transactions"
                    stroke="#2196f3"
                    strokeWidth={2}
                    name="Transactions"
                  />
                  <Line
                    type="monotone"
                    dataKey="alerts"
                    stroke="#f50057"
                    strokeWidth={2}
                    name="Alerts"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">API Health</Typography>
                  <Typography variant="body2" color="success.main">
                    Healthy
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={100} color="success" />
              </Box>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Database</Typography>
                  <Typography variant="body2" color="success.main">
                    Connected
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={100} color="success" />
              </Box>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Kafka</Typography>
                  <Typography variant="body2" color="success.main">
                    Streaming
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={100} color="success" />
              </Box>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">ML Models</Typography>
                  <Typography variant="body2" color="success.main">
                    Loaded
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={100} color="success" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Activity
              </Typography>
              <Typography variant="body2" color="textSecondary">
                • High-risk transaction detected: $1,250 at electronics store
              </Typography>
              <Typography variant="body2" color="textSecondary">
                • Impossible travel alert: Card used in US and UK within 5 minutes
              </Typography>
              <Typography variant="body2" color="textSecondary">
                • Velocity attack detected: 8 transactions in 1 hour
              </Typography>
              <Typography variant="body2" color="textSecondary">
                • Model retrained with 99.2% accuracy on new data
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;

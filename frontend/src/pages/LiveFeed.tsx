import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { format } from 'date-fns';

interface Transaction {
  txn_id: string;
  ts: string;
  amount: number;
  merchant_cat: string;
  merchant_id: string;
  score: number;
  is_alert: boolean;
  status: string;
}

const LiveFeed: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLive, setIsLive] = useState(true);
  const [loading, setLoading] = useState(false);

  // Mock data for demonstration
  const mockTransactions: Transaction[] = [
    {
      txn_id: 'txn_001',
      ts: new Date().toISOString(),
      amount: 125.50,
      merchant_cat: 'retail',
      merchant_id: 'WALMART_001',
      score: 0.15,
      is_alert: false,
      status: 'approved',
    },
    {
      txn_id: 'txn_002',
      ts: new Date(Date.now() - 30000).toISOString(),
      amount: 2500.00,
      merchant_cat: 'electronics',
      merchant_id: 'BESTBUY_001',
      score: 0.85,
      is_alert: true,
      status: 'flagged',
    },
    {
      txn_id: 'txn_003',
      ts: new Date(Date.now() - 60000).toISOString(),
      amount: 45.75,
      merchant_cat: 'food',
      merchant_id: 'STARBUCKS_001',
      score: 0.08,
      is_alert: false,
      status: 'approved',
    },
  ];

  useEffect(() => {
    if (isLive) {
      setTransactions(mockTransactions);
      
      // Simulate real-time updates
      const interval = setInterval(() => {
        const newTransaction: Transaction = {
          txn_id: `txn_${Date.now()}`,
          ts: new Date().toISOString(),
          amount: Math.random() * 1000,
          merchant_cat: ['retail', 'food', 'electronics', 'gas'][Math.floor(Math.random() * 4)],
          merchant_id: `MERCH_${Math.floor(Math.random() * 1000)}`,
          score: Math.random(),
          is_alert: Math.random() > 0.8,
          status: Math.random() > 0.8 ? 'flagged' : 'approved',
        };
        
        setTransactions(prev => [newTransaction, ...prev.slice(0, 49)]); // Keep last 50
      }, 3000);
      
      return () => clearInterval(interval);
    }
  }, [isLive]);

  const getScoreColor = (score: number) => {
    if (score > 0.7) return 'error';
    if (score > 0.4) return 'warning';
    return 'success';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'flagged':
        return 'error';
      case 'approved':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Live Transaction Feed
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={isLive}
              onChange={(e) => setIsLive(e.target.checked)}
              color="primary"
            />
          }
          label="Live Mode"
        />
      </Box>

      {loading && <LinearProgress />}

      <Card>
        <CardContent>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Transaction ID</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Merchant</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Fraud Score</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((txn) => (
                  <TableRow key={txn.txn_id} hover>
                    <TableCell>
                      {format(new Date(txn.ts), 'HH:mm:ss')}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {txn.txn_id.slice(-8)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        ${txn.amount.toFixed(2)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {txn.merchant_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={txn.merchant_cat}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        <Box sx={{ width: '100%', mr: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={txn.score * 100}
                            color={getScoreColor(txn.score) as any}
                            sx={{ height: 8, borderRadius: 4 }}
                          />
                        </Box>
                        <Typography variant="body2" minWidth={35}>
                          {(txn.score * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={txn.status}
                        color={getStatusColor(txn.status) as any}
                        size="small"
                        variant={txn.is_alert ? "filled" : "outlined"}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Box mt={2}>
        <Typography variant="body2" color="textSecondary">
          Showing {transactions.length} transactions • 
          {transactions.filter(t => t.is_alert).length} alerts • 
          Last updated: {format(new Date(), 'HH:mm:ss')}
        </Typography>
      </Box>
    </Box>
  );
};

export default LiveFeed;

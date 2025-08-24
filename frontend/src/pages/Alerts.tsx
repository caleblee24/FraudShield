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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  ExpandMore,
  Warning,
  Info,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import { format } from 'date-fns';
import axios from 'axios';

interface Alert {
  alert_id: string;
  txn_id: string;
  score: number;
  timestamp: string;
  status: string;
  explanation: any;
  analyst_notes?: string;
  resolution?: string;
}

const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  // Mock data for demonstration
  const mockAlerts: Alert[] = [
    {
      alert_id: 'alert_001',
      txn_id: 'txn_002',
      score: 0.85,
      timestamp: new Date().toISOString(),
      status: 'new',
      explanation: {
        top_contributing_features: [
          ['amount_z_score', 2.5],
          ['country_change', 1.0],
          ['txn_count_1h', 0.8],
        ],
        counterfactuals: [
          'Reduce transaction amount by 50%',
          'Use card in home country',
        ],
        risk_factors: {
          high_amount: true,
          geographic_anomaly: true,
          high_velocity: false,
        },
      },
    },
    {
      alert_id: 'alert_002',
      txn_id: 'txn_005',
      score: 0.72,
      timestamp: new Date(Date.now() - 300000).toISOString(),
      status: 'reviewing',
      explanation: {
        top_contributing_features: [
          ['merchant_fraud_rate', 0.15],
          ['device_rarity_score', 0.9],
          ['amount_z_score', 1.8],
        ],
        counterfactuals: [
          'Use different merchant',
          'Use familiar device',
        ],
        risk_factors: {
          high_amount: false,
          geographic_anomaly: false,
          suspicious_merchant: true,
        },
      },
      analyst_notes: 'Investigating device anomaly',
    },
  ];

  useEffect(() => {
    setAlerts(mockAlerts);
  }, []);

  const handleViewDetails = (alert: Alert) => {
    setSelectedAlert(alert);
    setDialogOpen(true);
  };

  const handleStatusChange = async (alertId: string, newStatus: string) => {
    try {
      // In real app, this would call the API
      setAlerts(prev => prev.map(alert => 
        alert.alert_id === alertId 
          ? { ...alert, status: newStatus }
          : alert
      ));
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new':
        return 'error';
      case 'reviewing':
        return 'warning';
      case 'resolved':
        return 'success';
      case 'false_positive':
        return 'info';
      default:
        return 'default';
    }
  };

  const getScoreColor = (score: number) => {
    if (score > 0.8) return 'error';
    if (score > 0.6) return 'warning';
    return 'info';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Fraud Alerts
      </Typography>

      <Card>
        <CardContent>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Alert ID</TableCell>
                  <TableCell>Transaction ID</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.alert_id} hover>
                    <TableCell>
                      {format(new Date(alert.timestamp), 'MMM dd, HH:mm')}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {alert.alert_id.slice(-8)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace">
                        {alert.txn_id.slice(-8)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${(alert.score * 100).toFixed(0)}%`}
                        color={getScoreColor(alert.score) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={alert.status}
                        color={getStatusColor(alert.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={() => handleViewDetails(alert)}
                      >
                        View Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Alert Details Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedAlert && (
          <>
            <DialogTitle>
              Alert Details - {selectedAlert.alert_id}
            </DialogTitle>
            <DialogContent>
              <Box mb={3}>
                <Typography variant="h6" gutterBottom>
                  Transaction Information
                </Typography>
                <Typography variant="body2">
                  Transaction ID: {selectedAlert.txn_id}
                </Typography>
                <Typography variant="body2">
                  Score: {(selectedAlert.score * 100).toFixed(1)}%
                </Typography>
                <Typography variant="body2">
                  Time: {format(new Date(selectedAlert.timestamp), 'PPP p')}
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="h6">
                    Risk Analysis
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    <Typography variant="subtitle1" gutterBottom>
                      Top Contributing Features:
                    </Typography>
                    <List dense>
                      {selectedAlert.explanation.top_contributing_features?.map(([feature, value]: [string, number], index: number) => (
                        <ListItem key={index}>
                          <ListItemText
                            primary={feature.replace(/_/g, ' ').toUpperCase()}
                            secondary={`Contribution: ${(value * 100).toFixed(1)}%`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="h6">
                    Counterfactual Explanations
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    {selectedAlert.explanation.counterfactuals?.map((cf: string, index: number) => (
                      <ListItem key={index}>
                        <ListItemText primary={cf} />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>

              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="h6">
                    Risk Factors
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box display="flex" flexWrap="wrap" gap={1}>
                    {Object.entries(selectedAlert.explanation.risk_factors || {}).map(([factor, isActive]) => (
                      <Chip
                        key={factor}
                        label={factor.replace(/_/g, ' ')}
                        color={isActive ? 'error' : 'default'}
                        variant={isActive ? 'filled' : 'outlined'}
                        size="small"
                      />
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>

              {selectedAlert.analyst_notes && (
                <Box mt={2}>
                  <Typography variant="h6" gutterBottom>
                    Analyst Notes
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {selectedAlert.analyst_notes}
                  </Typography>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button
                onClick={() => handleStatusChange(selectedAlert.alert_id, 'false_positive')}
                startIcon={<Cancel />}
                color="info"
              >
                Mark False Positive
              </Button>
              <Button
                onClick={() => handleStatusChange(selectedAlert.alert_id, 'resolved')}
                startIcon={<CheckCircle />}
                color="success"
              >
                Resolve
              </Button>
              <Button onClick={() => setDialogOpen(false)}>
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default Alerts;

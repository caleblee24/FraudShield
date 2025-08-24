import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  Alert,
  Chip,
  Slider,
  Divider,
} from '@mui/material';
import { PlayArrow, Stop, Refresh } from '@mui/icons-material';
import axios from 'axios';

interface SimulationScenario {
  name: string;
  description: string;
  scenario: string;
  parameters: Record<string, any>;
}

const Simulator: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [customAmount, setCustomAmount] = useState<number>(100);
  const [customCustomerId, setCustomCustomerId] = useState<string>('CUST001');

  const scenarios: SimulationScenario[] = [
    {
      name: 'Impossible Travel',
      description: 'Same card used in different countries within minutes',
      scenario: 'impossible_travel',
      parameters: {
        amount: 500,
        customer_id: 'CUST_FRAUD_001',
      },
    },
    {
      name: 'High Amount',
      description: 'Unusually large transaction amount',
      scenario: 'high_amount',
      parameters: {
        amount: 10000,
        customer_id: 'CUST_FRAUD_002',
      },
    },
    {
      name: 'Velocity Attack',
      description: 'Rapid-fire transactions in short time',
      scenario: 'velocity_attack',
      parameters: {
        amount: 50,
        customer_id: 'CUST_FRAUD_003',
      },
    },
    {
      name: 'Card Not Present',
      description: 'Online transaction with suspicious patterns',
      scenario: 'card_not_present',
      parameters: {
        amount: 200,
        customer_id: 'CUST_FRAUD_004',
      },
    },
  ];

  const handleSimulate = async (scenario: string, parameters: Record<string, any>) => {
    try {
      setIsRunning(true);
      const response = await axios.post('/simulate', {
        scenario,
        customer_id: parameters.customer_id || customCustomerId,
        amount: parameters.amount || customAmount,
      });
      
      setResults(prev => [...prev, {
        timestamp: new Date().toLocaleTimeString(),
        scenario,
        result: response.data,
      }]);
    } catch (error) {
      console.error('Simulation failed:', error);
      setResults(prev => [...prev, {
        timestamp: new Date().toLocaleTimeString(),
        scenario,
        error: 'Simulation failed',
      }]);
    } finally {
      setIsRunning(false);
    }
  };

  const handleBurstSimulation = async () => {
    setIsRunning(true);
    const burstResults = [];
    
    // Simulate multiple transactions in quick succession
    for (let i = 0; i < 5; i++) {
      try {
        const response = await axios.post('/simulate', {
          scenario: 'velocity_attack',
          customer_id: 'CUST_BURST_001',
          amount: 50 + (i * 25),
        });
        
        burstResults.push({
          timestamp: new Date().toLocaleTimeString(),
          scenario: 'velocity_attack',
          result: response.data,
        });
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (error) {
        burstResults.push({
          timestamp: new Date().toLocaleTimeString(),
          scenario: 'velocity_attack',
          error: 'Simulation failed',
        });
      }
    }
    
    setResults(prev => [...prev, ...burstResults]);
    setIsRunning(false);
  };

  const clearResults = () => {
    setResults([]);
  };

  const getScenarioByName = (name: string) => {
    return scenarios.find(s => s.name === name);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Fraud Simulator
      </Typography>
      
      <Grid container spacing={3}>
        {/* Scenario Selection */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Predefined Scenarios
              </Typography>
              
              <FormControl fullWidth margin="normal">
                <InputLabel>Select Scenario</InputLabel>
                <Select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  label="Select Scenario"
                >
                  {scenarios.map((scenario) => (
                    <MenuItem key={scenario.name} value={scenario.name}>
                      {scenario.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {selectedScenario && (
                <Box mt={2}>
                  <Typography variant="body2" color="textSecondary">
                    {getScenarioByName(selectedScenario)?.description}
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<PlayArrow />}
                    onClick={() => {
                      const scenario = getScenarioByName(selectedScenario);
                      if (scenario) {
                        handleSimulate(scenario.scenario, scenario.parameters);
                      }
                    }}
                    disabled={isRunning}
                    sx={{ mt: 2 }}
                  >
                    Run Scenario
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Custom Parameters */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Custom Parameters
              </Typography>
              
              <TextField
                fullWidth
                label="Customer ID"
                value={customCustomerId}
                onChange={(e) => setCustomCustomerId(e.target.value)}
                margin="normal"
              />
              
              <Box mt={2}>
                <Typography gutterBottom>Amount: ${customAmount}</Typography>
                <Slider
                  value={customAmount}
                  onChange={(_, value) => setCustomAmount(value as number)}
                  min={10}
                  max={10000}
                  step={10}
                  valueLabelDisplay="auto"
                />
              </Box>
              
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                onClick={() => handleSimulate('high_amount', { amount: customAmount, customer_id: customCustomerId })}
                disabled={isRunning}
                sx={{ mt: 2 }}
              >
                Simulate Custom
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Burst Simulation */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Burst Simulation
              </Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Simulate multiple rapid transactions to test velocity detection
              </Typography>
              
              <Button
                variant="contained"
                color="secondary"
                startIcon={<PlayArrow />}
                onClick={handleBurstSimulation}
                disabled={isRunning}
                sx={{ mr: 2 }}
              >
                Start Burst
              </Button>
              
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={clearResults}
                disabled={isRunning}
              >
                Clear Results
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Results */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Simulation Results
              </Typography>
              
              {results.length === 0 ? (
                <Typography color="textSecondary">
                  No simulations run yet. Select a scenario and click "Run Scenario" to start.
                </Typography>
              ) : (
                <Box>
                  {results.map((result, index) => (
                    <Box key={index} mb={2} p={2} border={1} borderColor="divider" borderRadius={1}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2">
                          {result.scenario} - {result.timestamp}
                        </Typography>
                        {result.error ? (
                          <Chip label="Failed" color="error" size="small" />
                        ) : (
                          <Chip label="Success" color="success" size="small" />
                        )}
                      </Box>
                      
                      {result.error ? (
                        <Alert severity="error">{result.error}</Alert>
                      ) : (
                        <Box>
                          <Typography variant="body2">
                            Transaction ID: {result.result.txn_id}
                          </Typography>
                          <Typography variant="body2">
                            Scenario: {result.result.scenario}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Simulator;

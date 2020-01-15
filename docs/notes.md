
# Icarus development Notes

## Progress

### AWS Resources

- historically, we have used the `c5d.9xlarge` ec2 instance for full scale Icarus simulations
- if we are bound to a single thread, it may be benefitial to use a `r5d.2xlarge` or `r5d.4xlarge` instance
- both of these are cheaper than the former by providing the needed storage and RAM without the unnecessary CPU cores

### Simulation

- As of yet, the simulation is not thread-safe in its current configuration.
- People at MATSim claim that the code should be robust enough to be thread-safe, but there are comments on functions across the error stack trace that suggest otherwise and the current runs of the simualtion do not run.
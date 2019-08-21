# MAG ABM Data Parsing

## Overview
The Maricopa Association of Governments (MAG) operates in Maricopa county conducting 
extensive research and data collection regarding the typical travel and activity 
behaviors of Maricopa residents. From their research, MAG has generated an 
Activity-Based Model (ABM) modeling at full scale and MAZ resolution the travel
and activity of the Maricopa population. This model is described in four interconnected 
tabular (CSV) datasets: 

- households 
- persons 
- trips
- vehicles

The files in this directory are designed to parse each of these datasets into a set
of MySQL tables.

---

## Source Data

### **Definitions**

### **Trips**
Vehicles enter the road going on a tour with a leader and a party (other 
occupants). Tours are comprised of subtours, which in turn are comprised of trips. 
Each row in the trips csv file represents a single trip.

- **hhid** - household id 
- **uniqueid** - trip index, unique per household
- **party** - list of vehicle occupants by person index, each unique per household
- **pnum** - trip leader as person index, unique per household
- **origTaz** - TAZ id of the starting location
- **destTaz** - TAZ id of the destination location
- **origMaz** - MAZ id of the starting location
- **destMaz** - MAZ id of the destination location 



### **Vehicles**

### **Persons**

### **Households**

---

## Output Data


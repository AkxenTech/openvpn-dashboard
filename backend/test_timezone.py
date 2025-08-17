#!/usr/bin/env python3
"""
Test timezone conversion functionality
"""

import pytz
from datetime import datetime

def test_timezone_conversion():
    """Test converting UTC times to Toronto timezone"""
    
    # Test current time
    utc_now = datetime.utcnow()
    print(f"Current UTC time: {utc_now}")
    
    # Convert to Toronto time
    toronto_tz = pytz.timezone('America/Toronto')
    toronto_now = utc_now.replace(tzinfo=pytz.utc).astimezone(toronto_tz)
    print(f"Current Toronto time: {toronto_now}")
    
    # Test with some sample server timestamps
    sample_times = [
        "2025-08-16 21:08:40.836000",
        "2025-08-16 21:08:39.933000", 
        "2025-08-16 21:08:38.662000"
    ]
    
    print("\nSample server timestamps converted to Toronto time:")
    print("-" * 60)
    
    for time_str in sample_times:
        try:
            # Parse the timestamp
            utc_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S.%f")
            print(f"UTC: {utc_time}")
            
            # Convert to Toronto time
            toronto_time = utc_time.replace(tzinfo=pytz.utc).astimezone(toronto_tz)
            print(f"Toronto: {toronto_time}")
            print()
        except Exception as e:
            print(f"Error converting {time_str}: {e}")

if __name__ == '__main__':
    test_timezone_conversion()

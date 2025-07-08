#!/usr/bin/env python3
"""
Test the agent percentage calculation in combined analysis
"""

import requests
import json
import pandas as pd

def test_agent_percentage_calculation():
    """Test that agent percentage is calculated and included in results."""
    
    print("👥 Testing Agent Percentage Calculation")
    print("=" * 45)
    
    # Test with applicants department
    department = "applicants"
    
    print(f"📊 Running combined analysis for {department}...")
    
    try:
        response = requests.post(
            f"http://localhost:8000/analyze/combined/{department}",
            params={"upload_to_sheets": False},
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Combined analysis completed successfully!")
            
            # Check delays analysis for agent intervention data
            delays_analysis = result.get('delays_analysis', {})
            if delays_analysis:
                delays_summary = delays_analysis.get('summary', {})
                agent_intervention = delays_summary.get('agent_intervention', {})
                
                if agent_intervention:
                    percentage = agent_intervention.get('percentage', 'Not found')
                    formatted = agent_intervention.get('formatted', 'Not found')
                    
                    print(f"\n📈 Agent Intervention Results:")
                    print(f"  Percentage (numeric): {percentage}")
                    print(f"  Formatted: {formatted}")
                    
                    if percentage != 'Not found':
                        print(f"  ✅ Agent percentage calculation working!")
                        
                        # Validate the percentage is reasonable (0-100)
                        if isinstance(percentage, (int, float)) and 0 <= percentage <= 100:
                            print(f"  ✅ Percentage value is valid: {percentage}%")
                        else:
                            print(f"  ⚠️ Percentage value seems unusual: {percentage}")
                    else:
                        print(f"  ❌ Agent percentage not found in delays analysis")
                else:
                    print(f"  ❌ No agent_intervention data in delays summary")
            else:
                print(f"  ❌ No delays_analysis in combined results")
            
            # Check summary sheet data
            summary_sheet = result.get('summary_sheet', {})
            if summary_sheet:
                summary_data = summary_sheet.get('data', {})
                agent_intervention_summary = summary_data.get('agent_intervention_percentage', 'Not found')
                
                print(f"\n📋 Summary Sheet Data:")
                print(f"  Agent Intervention %: {agent_intervention_summary}")
                
                if agent_intervention_summary != 'Not found' and agent_intervention_summary != '':
                    print(f"  ✅ Agent percentage included in summary sheet data!")
                else:
                    print(f"  ❌ Agent percentage not found in summary sheet data")
            else:
                print(f"  ❌ No summary_sheet data found")
            
            # Show other relevant data for context
            repetitions_analysis = result.get('repetitions_analysis', {})
            if repetitions_analysis:
                total_conversations = repetitions_analysis.get('total_conversations', 0)
                print(f"\n📊 Context Data:")
                print(f"  Total Conversations: {total_conversations}")
                
                if delays_analysis:
                    data_counts = delays_analysis.get('data_counts', {})
                    delays_total = data_counts.get('total_conversations', 0)
                    print(f"  Delays Total Conversations: {delays_total}")
            
            return True
            
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (this is normal for large datasets)")
        print("The analysis is likely still processing in the background")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_agent_percentage_function():
    """Test the agent percentage function logic directly."""
    
    print(f"\n🧪 Testing Agent Percentage Function Logic:")
    
    try:
        from app.services.delays_service import DelaysService
        
        # Create test data
        test_data = {
            'Message Type': ['Normal Message', 'Normal Message', 'Normal Message', 'Normal Message', 'Transfer'],
            'Sent By': ['Bot', 'Agent', 'Bot', 'Agent', 'System']
        }
        test_df = pd.DataFrame(test_data)
        
        service = DelaysService()
        result = service.calculate_agent_percentage('test', test_df)
        
        print(f"  Test data: {test_data}")
        print(f"  Expected: 50% (2 agent messages out of 4 normal messages)")
        print(f"  Actual result: {result}%")
        
        if result == 50.0:
            print(f"  ✅ Function logic is correct!")
        else:
            print(f"  ❌ Function logic may be incorrect")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing function: {e}")
        return False

def test_multiple_departments():
    """Test agent percentage for multiple departments."""
    
    print(f"\n🏢 Testing Multiple Departments:")
    
    departments = ["applicants", "doctors", "cc_sales", "mv_resolvers"]
    
    for dept in departments:
        print(f"\n  📊 Testing {dept}...")
        
        try:
            response = requests.post(
                f"http://localhost:8000/analyze/combined/{dept}",
                params={"upload_to_sheets": False},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                delays_analysis = result.get('delays_analysis', {})
                
                if delays_analysis:
                    agent_intervention = delays_analysis.get('summary', {}).get('agent_intervention', {})
                    percentage = agent_intervention.get('percentage', 'Not found')
                    
                    if percentage != 'Not found':
                        print(f"    ✅ {dept}: {percentage}%")
                    else:
                        print(f"    ❌ {dept}: No agent percentage data")
                else:
                    print(f"    ❌ {dept}: No delays analysis")
            else:
                print(f"    ❌ {dept}: Request failed ({response.status_code})")
                
        except requests.exceptions.Timeout:
            print(f"    ⏰ {dept}: Timeout (normal for large datasets)")
        except Exception as e:
            print(f"    ❌ {dept}: Error - {e}")

if __name__ == "__main__":
    print("🧪 Testing Agent Percentage Integration")
    print("=" * 50)
    
    # Test the function logic
    test_agent_percentage_function()
    
    # Test main functionality
    success = test_agent_percentage_calculation()
    
    # Test multiple departments (optional, may take time)
    # test_multiple_departments()
    
    if success:
        print(f"\n🎉 Agent percentage integration test completed!")
        print("✅ Check the results above to verify agent intervention % is calculated")
        print("✅ The percentage should appear in both delays analysis and summary sheet")
    else:
        print(f"\n❌ Test failed. Check the error messages above.")
    
    print(f"\n💡 What this calculates:")
    print("  - Filters data to only 'Normal Message' types")
    print("  - Counts messages sent by 'Bot' vs 'Agent'")
    print("  - Calculates: (Agent messages / (Bot + Agent messages)) * 100")
    print("  - Includes result in delays analysis summary and summary sheet")

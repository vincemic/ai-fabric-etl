#!/usr/bin/env python3
"""
Azure X12 Pipeline Cost Calculator
This script provides interactive cost estimation for the Azure Fabric X12 ETL pipeline
based on user inputs for transaction volume, file sizes, and processing frequency.
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Tuple

class X12PipelineCostCalculator:
    """Cost calculator for Azure X12 EDI processing pipeline"""
    
    def __init__(self):
        # Current pricing (East US 2, as of Sept 2025)
        self.pricing = {
            "storage": {
                "hot_gb_month": 0.0208,
                "cool_gb_month": 0.0115,
                "archive_gb_month": 0.002,
                "write_operations_per_10k": {"hot": 0.143, "cool": 0.260, "archive": 0.273},
                "read_operations_per_10k": {"hot": 0.0057, "cool": 0.013, "archive": 7.15},
                "data_retrieval_per_gb": {"hot": 0.0, "cool": 0.01, "archive": 0.022}
            },
            "data_factory": {
                "pipeline_activity_per_1k": 1.00,
                "copy_activity_per_1k": 0.25,
                "data_flow_per_hour": 0.274
            },
            "functions": {
                "consumption_gb_second": 0.000016,
                "consumption_per_million_executions": 0.20,
                "premium_ep1_month": 148.92,
                "premium_ep2_month": 297.84,
                "premium_ep3_month": 595.68,
                "free_gb_seconds_month": 400000,
                "free_executions_month": 1000000
            },
            "monitoring": {
                "log_analytics_ingestion_per_gb": 2.30,
                "log_analytics_retention_per_gb_month": 0.10,
                "free_data_gb_month": 5
            },
            "support_services": {
                "key_vault_operations_per_10k": 0.03,
                "service_bus_namespace_month": 10.00,
                "service_bus_operations_per_million": 0.05
            }
        }
    
    def calculate_storage_costs(self, total_data_gb: float, tier_distribution: Dict[str, float]) -> Dict[str, float]:
        """Calculate monthly storage costs based on data volume and tier distribution"""
        costs = {}
        
        for tier, percentage in tier_distribution.items():
            data_in_tier = total_data_gb * percentage
            monthly_cost = data_in_tier * self.pricing["storage"][f"{tier}_gb_month"]
            costs[f"{tier}_tier"] = round(monthly_cost, 2)
        
        costs["total_storage"] = round(sum(costs.values()), 2)
        return costs
    
    def calculate_data_factory_costs(self, transactions_per_month: int, activities_per_transaction: int = 3) -> Dict[str, float]:
        """Calculate Data Factory costs based on transaction volume"""
        total_activities = transactions_per_month * activities_per_transaction
        
        # Assume 70% pipeline activities, 30% copy activities
        pipeline_activities = total_activities * 0.7
        copy_activities = total_activities * 0.3
        
        pipeline_cost = (pipeline_activities / 1000) * self.pricing["data_factory"]["pipeline_activity_per_1k"]
        copy_cost = (copy_activities / 1000) * self.pricing["data_factory"]["copy_activity_per_1k"]
        
        total_cost = pipeline_cost + copy_cost
        
        return {
            "pipeline_activities": round(pipeline_cost, 2),
            "copy_activities": round(copy_cost, 2),
            "total_data_factory": round(total_cost, 2)
        }
    
    def calculate_function_costs(self, transactions_per_month: int, 
                               execution_time_seconds: float = 30, 
                               memory_gb: float = 0.5,
                               plan_type: str = "consumption") -> Dict[str, float]:
        """Calculate Azure Functions costs"""
        
        if plan_type == "consumption":
            executions = transactions_per_month * 2  # Assume 2 function calls per transaction
            gb_seconds = executions * execution_time_seconds * memory_gb
            
            # Apply free tier
            billable_gb_seconds = max(0, gb_seconds - self.pricing["functions"]["free_gb_seconds_month"])
            billable_executions = max(0, executions - self.pricing["functions"]["free_executions_month"])
            
            execution_cost = billable_gb_seconds * self.pricing["functions"]["consumption_gb_second"]
            invocation_cost = (billable_executions / 1000000) * self.pricing["functions"]["consumption_per_million_executions"]
            
            total_cost = execution_cost + invocation_cost
            
            return {
                "execution_cost": round(execution_cost, 2),
                "invocation_cost": round(invocation_cost, 2),
                "total_functions": round(total_cost, 2),
                "plan_type": "consumption"
            }
        
        elif plan_type.startswith("premium"):
            plan_cost = self.pricing["functions"][f"{plan_type}_month"]
            return {
                "plan_cost": plan_cost,
                "total_functions": plan_cost,
                "plan_type": plan_type
            }
    
    def calculate_monitoring_costs(self, total_monthly_cost: float, 
                                 log_volume_gb_month: float = None) -> Dict[str, float]:
        """Calculate monitoring and logging costs"""
        
        if log_volume_gb_month is None:
            # Estimate log volume as 0.5% of total data processed
            log_volume_gb_month = total_monthly_cost * 0.005
        
        # Apply free tier
        billable_log_volume = max(0, log_volume_gb_month - self.pricing["monitoring"]["free_data_gb_month"])
        
        ingestion_cost = billable_log_volume * self.pricing["monitoring"]["log_analytics_ingestion_per_gb"]
        retention_cost = billable_log_volume * self.pricing["monitoring"]["log_analytics_retention_per_gb_month"]
        
        total_cost = ingestion_cost + retention_cost
        
        return {
            "log_ingestion": round(ingestion_cost, 2),
            "log_retention": round(retention_cost, 2),
            "total_monitoring": round(total_cost, 2)
        }
    
    def calculate_support_services_costs(self, transactions_per_month: int) -> Dict[str, float]:
        """Calculate supporting services costs (Key Vault, Service Bus, etc.)"""
        
        # Key Vault operations (assume 5 operations per transaction)
        kv_operations = transactions_per_month * 5
        kv_cost = (kv_operations / 10000) * self.pricing["support_services"]["key_vault_operations_per_10k"]
        
        # Service Bus (base cost + operations)
        sb_base_cost = self.pricing["support_services"]["service_bus_namespace_month"]
        sb_operations = transactions_per_month * 2  # Assume 2 messages per transaction
        sb_operations_cost = (sb_operations / 1000000) * self.pricing["support_services"]["service_bus_operations_per_million"]
        
        total_cost = kv_cost + sb_base_cost + sb_operations_cost
        
        return {
            "key_vault": round(kv_cost, 2),
            "service_bus_base": sb_base_cost,
            "service_bus_operations": round(sb_operations_cost, 2),
            "total_support_services": round(total_cost, 2)
        }
    
    def calculate_total_costs(self, 
                            transactions_per_month: int,
                            avg_file_size_kb: int = 75,
                            processing_frequency: str = "hourly",
                            function_plan: str = "consumption") -> Dict[str, Any]:
        """Calculate total pipeline costs for given parameters"""
        
        # Calculate total data volume
        total_data_gb = (transactions_per_month * avg_file_size_kb) / (1024 * 1024)
        
        # Determine tier distribution based on processing frequency
        tier_distributions = {
            "daily": {"hot": 0.2, "cool": 0.6, "archive": 0.2},
            "hourly": {"hot": 0.3, "cool": 0.5, "archive": 0.2},
            "realtime": {"hot": 0.5, "cool": 0.4, "archive": 0.1}
        }
        
        tier_distribution = tier_distributions.get(processing_frequency, tier_distributions["hourly"])
        
        # Calculate frequency multiplier
        frequency_multipliers = {
            "daily": 1.0,
            "hourly": 1.8,
            "realtime": 3.0
        }
        
        frequency_multiplier = frequency_multipliers.get(processing_frequency, 1.8)
        
        # Calculate component costs
        storage_costs = self.calculate_storage_costs(total_data_gb, tier_distribution)
        
        data_factory_costs = self.calculate_data_factory_costs(transactions_per_month)
        # Apply frequency multiplier to Data Factory costs
        data_factory_costs = {k: v * frequency_multiplier if k != "total_data_factory" else v * frequency_multiplier 
                            for k, v in data_factory_costs.items()}
        
        function_costs = self.calculate_function_costs(transactions_per_month, plan_type=function_plan)
        
        support_costs = self.calculate_support_services_costs(transactions_per_month)
        
        # Calculate preliminary total for monitoring estimation
        preliminary_total = (storage_costs["total_storage"] + 
                           data_factory_costs["total_data_factory"] + 
                           function_costs["total_functions"] + 
                           support_costs["total_support_services"])
        
        monitoring_costs = self.calculate_monitoring_costs(preliminary_total)
        
        # Calculate final total
        total_monthly_cost = (storage_costs["total_storage"] + 
                            data_factory_costs["total_data_factory"] + 
                            function_costs["total_functions"] + 
                            monitoring_costs["total_monitoring"] + 
                            support_costs["total_support_services"])
        
        cost_per_transaction = total_monthly_cost / transactions_per_month if transactions_per_month > 0 else 0
        
        return {
            "input_parameters": {
                "transactions_per_month": transactions_per_month,
                "avg_file_size_kb": avg_file_size_kb,
                "processing_frequency": processing_frequency,
                "function_plan": function_plan,
                "total_data_gb": round(total_data_gb, 2)
            },
            "cost_breakdown": {
                "storage": storage_costs,
                "data_factory": data_factory_costs,
                "functions": function_costs,
                "monitoring": monitoring_costs,
                "support_services": support_costs
            },
            "summary": {
                "total_monthly_cost": round(total_monthly_cost, 2),
                "cost_per_transaction": round(cost_per_transaction, 6),
                "frequency_multiplier": frequency_multiplier
            },
            "calculation_date": datetime.now().isoformat()
        }

def interactive_calculator():
    """Interactive cost calculator"""
    calculator = X12PipelineCostCalculator()
    
    print("=" * 60)
    print("Azure X12 Pipeline Cost Calculator")
    print("=" * 60)
    
    try:
        # Get user inputs
        print("\nPlease provide the following information:")
        
        transactions = int(input("Number of X12 transactions per month: "))
        file_size = int(input("Average file size in KB (default 75): ") or "75")
        
        print("\nProcessing frequency options:")
        print("1. Daily batch processing")
        print("2. Hourly processing")
        print("3. Real-time/continuous processing")
        freq_choice = input("Select frequency (1-3, default 2): ") or "2"
        
        frequency_map = {"1": "daily", "2": "hourly", "3": "realtime"}
        frequency = frequency_map.get(freq_choice, "hourly")
        
        print("\nAzure Functions plan options:")
        print("1. Consumption (pay-as-you-go)")
        print("2. Premium EP1 ($148.92/month)")
        print("3. Premium EP2 ($297.84/month)")
        plan_choice = input("Select plan (1-3, default 1): ") or "1"
        
        plan_map = {"1": "consumption", "2": "premium_ep1", "3": "premium_ep2"}
        function_plan = plan_map.get(plan_choice, "consumption")
        
        # Calculate costs
        print("\nCalculating costs...")
        results = calculator.calculate_total_costs(
            transactions_per_month=transactions,
            avg_file_size_kb=file_size,
            processing_frequency=frequency,
            function_plan=function_plan
        )
        
        # Display results
        print("\n" + "=" * 60)
        print("COST ESTIMATION RESULTS")
        print("=" * 60)
        
        print(f"\nInput Parameters:")
        print(f"  Transactions per month: {results['input_parameters']['transactions_per_month']:,}")
        print(f"  Average file size: {results['input_parameters']['avg_file_size_kb']} KB")
        print(f"  Processing frequency: {results['input_parameters']['processing_frequency']}")
        print(f"  Function plan: {results['input_parameters']['function_plan']}")
        print(f"  Total data volume: {results['input_parameters']['total_data_gb']} GB/month")
        
        print(f"\nCost Breakdown:")
        breakdown = results['cost_breakdown']
        print(f"  Storage: ${breakdown['storage']['total_storage']}")
        print(f"  Data Factory: ${breakdown['data_factory']['total_data_factory']}")
        print(f"  Functions: ${breakdown['functions']['total_functions']}")
        print(f"  Monitoring: ${breakdown['monitoring']['total_monitoring']}")
        print(f"  Support Services: ${breakdown['support_services']['total_support_services']}")
        
        print(f"\nSummary:")
        summary = results['summary']
        print(f"  Total monthly cost: ${summary['total_monthly_cost']}")
        print(f"  Cost per transaction: ${summary['cost_per_transaction']}")
        
        # Save results
        output_file = f"cost_estimate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        # Cost optimization suggestions
        print(f"\nCost Optimization Suggestions:")
        if summary['total_monthly_cost'] > 1000:
            print("  - Consider implementing storage lifecycle management")
            print("  - Evaluate Premium Functions plan for predictable costs")
            print("  - Implement data compression to reduce storage costs")
        
        if breakdown['storage']['total_storage'] > summary['total_monthly_cost'] * 0.5:
            print("  - Storage is a major cost driver - optimize tier distribution")
            print("  - Consider archiving older data more aggressively")
        
        if breakdown['data_factory']['total_data_factory'] > summary['total_monthly_cost'] * 0.4:
            print("  - Data Factory costs are high - optimize pipeline activities")
            print("  - Consider batching smaller files together")
    
    except KeyboardInterrupt:
        print("\n\nCalculation cancelled by user.")
        sys.exit(0)
    except ValueError as e:
        print(f"\nError: Invalid input - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

def batch_calculator(scenarios_file: str):
    """Calculate costs for multiple scenarios from a JSON file"""
    calculator = X12PipelineCostCalculator()
    
    try:
        with open(scenarios_file, 'r') as f:
            scenarios = json.load(f)
        
        results = []
        
        for scenario in scenarios:
            print(f"Calculating costs for scenario: {scenario.get('name', 'Unnamed')}")
            
            cost_result = calculator.calculate_total_costs(
                transactions_per_month=scenario['transactions_per_month'],
                avg_file_size_kb=scenario.get('avg_file_size_kb', 75),
                processing_frequency=scenario.get('processing_frequency', 'hourly'),
                function_plan=scenario.get('function_plan', 'consumption')
            )
            
            cost_result['scenario_name'] = scenario.get('name', 'Unnamed')
            results.append(cost_result)
        
        # Save batch results
        output_file = f"batch_cost_estimates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nBatch calculation results saved to: {output_file}")
        
        # Display summary comparison
        print("\nScenario Comparison:")
        print("-" * 80)
        print(f"{'Scenario':<20} {'Transactions':<12} {'Monthly Cost':<12} {'Per Transaction':<15}")
        print("-" * 80)
        
        for result in results:
            name = result['scenario_name'][:19]
            transactions = f"{result['input_parameters']['transactions_per_month']:,}"
            monthly_cost = f"${result['summary']['total_monthly_cost']}"
            per_transaction = f"${result['summary']['cost_per_transaction']}"
            print(f"{name:<20} {transactions:<12} {monthly_cost:<12} {per_transaction:<15}")
    
    except FileNotFoundError:
        print(f"Error: Scenarios file '{scenarios_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in scenarios file '{scenarios_file}'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing scenarios: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Interactive mode
        interactive_calculator()
    elif len(sys.argv) == 2:
        # Batch mode with scenarios file
        batch_calculator(sys.argv[1])
    else:
        print("Usage:")
        print("  python cost_calculator.py                    # Interactive mode")
        print("  python cost_calculator.py scenarios.json    # Batch mode")
        sys.exit(1)
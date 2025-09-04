#!/usr/bin/env python3
"""
Additional Test Data Generator for Azure Fabric ETL Pipeline
Generates more comprehensive test data with various scenarios.
"""

import json
import random
import datetime
import os
from typing import Dict, List, Optional

class EnhancedX12TestDataGenerator:
    """Enhanced generator for X12 test data with more realistic scenarios."""
    
    def __init__(self):
        self.transaction_types = {
            "837": "Health Care Claim",
            "835": "Health Care Claim Payment/Advice", 
            "834": "Benefit Enrollment and Maintenance",
            "270": "Health Care Eligibility Benefit Inquiry",
            "271": "Health Care Eligibility Benefit Response",
            "276": "Health Care Claim Status Request",
            "277": "Health Care Claim Status Response",
            "278": "Health Care Services Review Request",
            "279": "Health Care Services Review Response"
        }
        
        # X12 control characters
        self.element_separator = "*"
        self.segment_terminator = "~"
        self.component_separator = ":"
        
        # Test providers and payers
        self.providers = [
            {"name": "MAIN STREET CLINIC", "npi": "1234567890", "id": "MSC001"},
            {"name": "DOWNTOWN HOSPITAL", "npi": "2345678901", "id": "DTH002"},
            {"name": "FAMILY CARE CENTER", "npi": "3456789012", "id": "FCC003"},
            {"name": "SPECIALTY PHYSICIANS", "npi": "4567890123", "id": "SPC004"},
            {"name": "URGENT CARE PLUS", "npi": "5678901234", "id": "UCP005"}
        ]
        
        self.payers = [
            {"name": "BLUE CROSS BLUE SHIELD", "id": "BCBS001"},
            {"name": "AETNA HEALTH PLANS", "id": "AETNA02"},
            {"name": "UNITED HEALTHCARE", "id": "UHC0003"},
            {"name": "CIGNA HEALTHCARE", "id": "CIGNA04"},
            {"name": "HUMANA MEDICAL", "id": "HUMANA5"}
        ]
        
    def generate_control_number(self) -> str:
        """Generate a unique control number."""
        return f"{random.randint(100000000, 999999999)}"
    
    def generate_date(self, days_offset: int = 0) -> str:
        """Generate a date with optional offset from today."""
        base_date = datetime.datetime.now()
        if days_offset == 0:
            random_days = random.randint(-90, 30)
        else:
            random_days = days_offset
        test_date = base_date + datetime.timedelta(days=random_days)
        return test_date.strftime("%Y%m%d")
    
    def generate_time(self) -> str:
        """Generate a random time in HHMM format."""
        return f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
    
    def generate_isa_header(self, sender: dict, receiver: dict) -> str:
        """Generate ISA (Interchange Control Header) segment."""
        control_number = self.generate_control_number()
        date = self.generate_date()
        time = self.generate_time()
        
        return (
            f"ISA{self.element_separator}"
            f"00{self.element_separator}"
            f"          {self.element_separator}"
            f"00{self.element_separator}"
            f"          {self.element_separator}"
            f"ZZ{self.element_separator}"
            f"{sender['id']:<15}{self.element_separator}"
            f"ZZ{self.element_separator}"
            f"{receiver['id']:<15}{self.element_separator}"
            f"{date}{self.element_separator}"
            f"{time}{self.element_separator}"
            f"^{self.element_separator}"
            f"00501{self.element_separator}"
            f"{control_number}{self.element_separator}"
            f"0{self.element_separator}"
            f"T{self.element_separator}"
            f"{self.component_separator}{self.segment_terminator}"
        )
    
    def generate_837_professional_claim(self, provider: dict) -> List[str]:
        """Generate a more detailed 837 Professional claim."""
        segments = []
        
        # BHT - Beginning of Hierarchical Transaction
        segments.append(
            f"BHT{self.element_separator}0019{self.element_separator}00{self.element_separator}"
            f"CLM{self.generate_control_number()}{self.element_separator}{self.generate_date()}{self.element_separator}"
            f"{self.generate_time()}{self.segment_terminator}"
        )
        
        # NM1 - Submitter Name
        segments.append(
            f"NM1{self.element_separator}41{self.element_separator}2{self.element_separator}"
            f"{provider['name']}{self.element_separator}{self.element_separator}{self.element_separator}"
            f"{self.element_separator}{self.element_separator}XX{self.element_separator}"
            f"{provider['npi']}{self.segment_terminator}"
        )
        
        # PER - Submitter EDI Contact Information
        segments.append(
            f"PER{self.element_separator}IC{self.element_separator}BILLING DEPT{self.element_separator}"
            f"TE{self.element_separator}{random.randint(5550000000, 5559999999)}{self.element_separator}"
            f"EM{self.element_separator}billing@{provider['id'].lower()}.com{self.segment_terminator}"
        )
        
        # NM1 - Receiver Name (Payer)
        payer = random.choice(self.payers)
        segments.append(
            f"NM1{self.element_separator}40{self.element_separator}2{self.element_separator}"
            f"{payer['name']}{self.element_separator}{self.element_separator}{self.element_separator}"
            f"{self.element_separator}{self.element_separator}46{self.element_separator}"
            f"{payer['id']}{self.segment_terminator}"
        )
        
        # Hierarchical levels for subscriber, patient, claim
        segments.append(f"HL{self.element_separator}1{self.element_separator}{self.element_separator}20{self.element_separator}1{self.segment_terminator}")
        segments.append(f"HL{self.element_separator}2{self.element_separator}1{self.element_separator}22{self.element_separator}0{self.segment_terminator}")
        
        # CLM - Claim Information
        claim_amount = f"{random.randint(50, 5000)}.00"
        segments.append(
            f"CLM{self.element_separator}CLM{random.randint(1000, 9999)}{self.element_separator}"
            f"{claim_amount}{self.element_separator}{self.element_separator}{self.element_separator}"
            f"11{self.component_separator}A{self.component_separator}1{self.element_separator}"
            f"Y{self.element_separator}A{self.element_separator}Y{self.element_separator}Y{self.segment_terminator}"
        )
        
        # Service line information
        procedure_codes = ["99213", "99214", "99215", "99396", "99397", "90834", "90837"]
        procedure_code = random.choice(procedure_codes)
        service_amount = f"{random.randint(75, 500)}.00"
        
        segments.append(
            f"SV1{self.element_separator}HC{self.component_separator}{procedure_code}{self.element_separator}"
            f"{service_amount}{self.element_separator}UN{self.element_separator}1{self.element_separator}"
            f"{self.element_separator}{self.element_separator}{self.element_separator}"
            f"1{self.segment_terminator}"
        )
        
        # Date of service
        segments.append(
            f"DTP{self.element_separator}472{self.element_separator}D8{self.element_separator}"
            f"{self.generate_date(-random.randint(1, 30))}{self.segment_terminator}"
        )
        
        return segments
    
    def generate_835_detailed_payment(self, payer: dict) -> List[str]:
        """Generate a detailed 835 payment advice."""
        segments = []
        
        # BPR - Financial Information
        total_amount = f"{random.randint(1000, 50000)}.00"
        segments.append(
            f"BPR{self.element_separator}I{self.element_separator}{total_amount}{self.element_separator}"
            f"C{self.element_separator}ACH{self.element_separator}CCP{self.element_separator}"
            f"01{self.element_separator}123456789{self.element_separator}DA{self.element_separator}"
            f"987654321{self.element_separator}{payer['id']}{self.element_separator}{self.element_separator}"
            f"01{self.element_separator}987654321{self.element_separator}DA{self.element_separator}"
            f"123456789{self.element_separator}{self.generate_date()}{self.segment_terminator}"
        )
        
        # TRN - Reassociation Trace Number
        segments.append(
            f"TRN{self.element_separator}1{self.element_separator}EFT{self.generate_control_number()}{self.element_separator}"
            f"{payer['id']}{self.segment_terminator}"
        )
        
        # N1 - Payer Identification
        segments.append(
            f"N1{self.element_separator}PR{self.element_separator}{payer['name']}{self.segment_terminator}"
        )
        
        # N3 - Payer Address
        segments.append(
            f"N3{self.element_separator}{random.randint(100, 9999)} INSURANCE BLVD{self.segment_terminator}"
        )
        
        # N4 - Payer City, State, ZIP
        cities = ["DALLAS", "CHICAGO", "ATLANTA", "PHOENIX", "DENVER"]
        states = ["TX", "IL", "GA", "AZ", "CO"]
        city_state = random.choice(list(zip(cities, states)))
        segments.append(
            f"N4{self.element_separator}{city_state[0]}{self.element_separator}{city_state[1]}{self.element_separator}"
            f"{random.randint(10000, 99999)}{self.segment_terminator}"
        )
        
        return segments
    
    def generate_complete_transaction(self, transaction_type: str, provider: dict = None, payer: dict = None) -> str:
        """Generate a complete X12 transaction with realistic data."""
        if not provider:
            provider = random.choice(self.providers)
        if not payer:
            payer = random.choice(self.payers)
            
        segments = []
        
        # ISA Header
        segments.append(self.generate_isa_header(provider, payer))
        
        # Functional codes
        functional_codes = {
            "837": "HC", "835": "HP", "834": "BE", "270": "HS", "271": "HS",
            "276": "HR", "277": "HR", "278": "HN", "279": "HN"
        }
        
        # GS Header
        control_number = self.generate_control_number()
        segments.append(
            f"GS{self.element_separator}{functional_codes[transaction_type]}{self.element_separator}"
            f"{provider['id']}{self.element_separator}{payer['id']}{self.element_separator}"
            f"{self.generate_date()}{self.element_separator}{self.generate_time()}{self.element_separator}"
            f"{control_number}{self.element_separator}X{self.element_separator}005010X222A1{self.segment_terminator}"
        )
        
        # ST Header
        st_control = self.generate_control_number()
        segments.append(f"ST{self.element_separator}{transaction_type}{self.element_separator}{st_control}{self.segment_terminator}")
        
        # Transaction-specific content
        if transaction_type == "837":
            segments.extend(self.generate_837_professional_claim(provider))
        elif transaction_type == "835":
            segments.extend(self.generate_835_detailed_payment(payer))
        
        # SE Trailer
        segment_count = len(segments) + 1
        segments.append(f"SE{self.element_separator}{segment_count}{self.element_separator}{st_control}{self.segment_terminator}")
        
        # GE Trailer
        segments.append(f"GE{self.element_separator}1{self.element_separator}{control_number}{self.segment_terminator}")
        
        # IEA Trailer
        isa_control = self.generate_control_number()
        segments.append(f"IEA{self.element_separator}1{self.element_separator}{isa_control}{self.segment_terminator}")
        
        return "".join(segments)
    
    def generate_scenario_files(self, scenario_name: str, file_count: int, transaction_types: List[str]) -> List[str]:
        """Generate files for a specific test scenario."""
        scenario_dir = os.path.join("scenarios", scenario_name)
        if not os.path.exists(scenario_dir):
            os.makedirs(scenario_dir)
        
        generated_files = []
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i in range(file_count):
            transaction_type = random.choice(transaction_types)
            provider = random.choice(self.providers)
            payer = random.choice(self.payers)
            
            content = self.generate_complete_transaction(transaction_type, provider, payer)
            
            filename = f"{scenario_name}_{transaction_type}_{provider['id']}_{payer['id']}_{timestamp}_{i:03d}.x12"
            filepath = os.path.join(scenario_dir, filename)
            
            with open(filepath, 'w', encoding='ascii') as f:
                f.write(content)
            
            generated_files.append(filepath)
            print(f"  Generated: {filename}")
        
        return generated_files

def main():
    """Generate test data for various scenarios."""
    generator = EnhancedX12TestDataGenerator()
    
    # Define test scenarios
    scenarios = [
        {
            "name": "development",
            "description": "Basic development testing",
            "file_count": 15,
            "transaction_types": ["837", "835", "270", "271"]
        },
        {
            "name": "claims_processing",
            "description": "Claims and payments focus",
            "file_count": 20,
            "transaction_types": ["837", "835"]
        },
        {
            "name": "eligibility_verification",
            "description": "Eligibility inquiries and responses",
            "file_count": 10,
            "transaction_types": ["270", "271"]
        },
        {
            "name": "status_requests",
            "description": "Claim status requests and responses",
            "file_count": 8,
            "transaction_types": ["276", "277"]
        }
    ]
    
    print("Enhanced X12 Test Data Generator")
    print("=" * 50)
    
    total_files = 0
    for scenario in scenarios:
        print(f"\nGenerating {scenario['name']} scenario ({scenario['description']})...")
        files = generator.generate_scenario_files(
            scenario["name"],
            scenario["file_count"],
            scenario["transaction_types"]
        )
        total_files += len(files)
    
    print(f"\n✓ Generated {total_files} test files across {len(scenarios)} scenarios")
    
    # Create a summary report
    summary = {
        "generation_date": datetime.datetime.now().isoformat(),
        "total_files": total_files,
        "scenarios": scenarios,
        "providers": generator.providers,
        "payers": generator.payers,
        "transaction_types": generator.transaction_types
    }
    
    with open("test_data_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n✓ Created test_data_summary.json with generation details")
    print("\nNext steps:")
    print("1. Review generated files in the scenarios/ subdirectories")
    print("2. Upload to Azure storage for pipeline testing")
    print("3. Monitor processing through Azure Data Factory")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
X12 Test Data Generator for Azure Fabric ETL Pipeline
Generates sample HIPAA X12 transaction files for testing purposes.
"""

import json
import random
import datetime
from typing import Dict, List, Optional
import os

class X12TestDataGenerator:
    """Generate test X12 HIPAA transaction files for testing the ETL pipeline."""
    
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
        
    def generate_control_number(self) -> str:
        """Generate a unique control number."""
        return f"{random.randint(100000000, 999999999)}"
    
    def generate_date(self, format_type: str = "CCYYMMDD") -> str:
        """Generate a random date in specified format."""
        base_date = datetime.datetime.now()
        random_days = random.randint(-30, 30)
        test_date = base_date + datetime.timedelta(days=random_days)
        
        if format_type == "CCYYMMDD":
            return test_date.strftime("%Y%m%d")
        elif format_type == "HHMM":
            return test_date.strftime("%H%M")
        return test_date.strftime("%Y%m%d")
    
    def generate_time(self) -> str:
        """Generate a random time in HHMM format."""
        return f"{random.randint(0, 23):02d}{random.randint(0, 59):02d}"
    
    def generate_isa_header(self, sender_id: str = "SENDER01", receiver_id: str = "RECEIVER01") -> str:
        """Generate ISA (Interchange Control Header) segment."""
        control_number = self.generate_control_number()
        date = self.generate_date()
        time = self.generate_time()
        
        isa_segment = (
            f"ISA{self.element_separator}"
            f"00{self.element_separator}"  # Authorization Information Qualifier
            f"          {self.element_separator}"  # Authorization Information (10 spaces)
            f"00{self.element_separator}"  # Security Information Qualifier
            f"          {self.element_separator}"  # Security Information (10 spaces)
            f"ZZ{self.element_separator}"  # Interchange ID Qualifier (Sender)
            f"{sender_id:<15}{self.element_separator}"  # Interchange Sender ID
            f"ZZ{self.element_separator}"  # Interchange ID Qualifier (Receiver)
            f"{receiver_id:<15}{self.element_separator}"  # Interchange Receiver ID
            f"{date}{self.element_separator}"  # Interchange Date
            f"{time}{self.element_separator}"  # Interchange Time
            f"^{self.element_separator}"  # Repetition Separator
            f"00501{self.element_separator}"  # Interchange Control Version Number
            f"{control_number}{self.element_separator}"  # Interchange Control Number
            f"0{self.element_separator}"  # Acknowledgment Requested
            f"T{self.element_separator}"  # Usage Indicator (T=Test)
            f"{self.component_separator}{self.segment_terminator}"  # Component Element Separator
        )
        return isa_segment
    
    def generate_gs_header(self, functional_code: str, sender_code: str = "SENDER01", 
                          receiver_code: str = "RECEIVER01") -> str:
        """Generate GS (Functional Group Header) segment."""
        control_number = self.generate_control_number()
        date = self.generate_date()
        time = self.generate_time()
        
        gs_segment = (
            f"GS{self.element_separator}"
            f"{functional_code}{self.element_separator}"  # Functional Identifier Code
            f"{sender_code}{self.element_separator}"  # Application Sender's Code
            f"{receiver_code}{self.element_separator}"  # Application Receiver's Code
            f"{date}{self.element_separator}"  # Date
            f"{time}{self.element_separator}"  # Time
            f"{control_number}{self.element_separator}"  # Group Control Number
            f"X{self.element_separator}"  # Responsible Agency Code
            f"005010X222A1{self.segment_terminator}"  # Version/Release/Industry Identifier Code
        )
        return gs_segment
    
    def generate_st_header(self, transaction_set_id: str) -> str:
        """Generate ST (Transaction Set Header) segment."""
        control_number = self.generate_control_number()
        st_segment = (
            f"ST{self.element_separator}"
            f"{transaction_set_id}{self.element_separator}"  # Transaction Set Identifier Code
            f"{control_number}{self.segment_terminator}"  # Transaction Set Control Number
        )
        return st_segment, control_number
    
    def generate_837_claim(self, provider_npi: str = "1234567890") -> List[str]:
        """Generate sample 837 Health Care Claim transaction."""
        segments = []
        
        # BHT - Beginning of Hierarchical Transaction
        segments.append(
            f"BHT{self.element_separator}"
            f"0019{self.element_separator}"  # Hierarchical Structure Code
            f"00{self.element_separator}"  # Transaction Set Purpose Code
            f"0001{self.element_separator}"  # Reference Identification
            f"{self.generate_date()}{self.element_separator}"  # Date
            f"{self.generate_time()}{self.segment_terminator}"  # Time
        )
        
        # NM1 - Individual or Organizational Name (Submitter)
        segments.append(
            f"NM1{self.element_separator}"
            f"41{self.element_separator}"  # Entity Identifier Code (Submitter)
            f"2{self.element_separator}"  # Entity Type Qualifier (Non-Person)
            f"TEST CLINIC{self.element_separator}"  # Name Last or Organization Name
            f"{self.element_separator}"  # Name First
            f"{self.element_separator}"  # Name Middle
            f"{self.element_separator}"  # Name Prefix
            f"{self.element_separator}"  # Name Suffix
            f"XX{self.element_separator}"  # Identification Code Qualifier
            f"{provider_npi}{self.segment_terminator}"  # Identification Code
        )
        
        # PER - Administrative Communications Contact
        segments.append(
            f"PER{self.element_separator}"
            f"IC{self.element_separator}"  # Contact Function Code
            f"TEST CONTACT{self.element_separator}"  # Name
            f"TE{self.element_separator}"  # Communication Number Qualifier
            f"5551234567{self.segment_terminator}"  # Communication Number
        )
        
        # Add more 837-specific segments as needed...
        
        return segments
    
    def generate_835_payment(self) -> List[str]:
        """Generate sample 835 Health Care Claim Payment/Advice transaction."""
        segments = []
        
        # BPR - Financial Information
        segments.append(
            f"BPR{self.element_separator}"
            f"I{self.element_separator}"  # Transaction Handling Code
            f"1500.00{self.element_separator}"  # Monetary Amount
            f"C{self.element_separator}"  # Credit/Debit Flag Code
            f"ACH{self.element_separator}"  # Payment Method Code
            f"CCP{self.element_separator}"  # Payment Format Code
            f"{self.element_separator}"  # DFI ID Number Qualifier
            f"{self.element_separator}"  # DFI Identification Number
            f"{self.element_separator}"  # Account Number Qualifier
            f"{self.element_separator}"  # Account Number
            f"{self.element_separator}"  # Originating Company Identifier
            f"{self.element_separator}"  # Originating Company Supplemental Code
            f"{self.element_separator}"  # DFI ID Number Qualifier
            f"{self.element_separator}"  # DFI Identification Number
            f"{self.element_separator}"  # Account Number Qualifier
            f"{self.element_separator}"  # Account Number
            f"{self.generate_date()}{self.segment_terminator}"  # Effective Date
        )
        
        # TRN - Trace Number
        segments.append(
            f"TRN{self.element_separator}"
            f"1{self.element_separator}"  # Trace Type Code
            f"{self.generate_control_number()}{self.element_separator}"  # Reference Identification
            f"1234567890{self.segment_terminator}"  # Originating Company Identifier
        )
        
        return segments
    
    def generate_270_eligibility_inquiry(self) -> List[str]:
        """Generate sample 270 Health Care Eligibility Benefit Inquiry transaction."""
        segments = []
        
        # BHT - Beginning of Hierarchical Transaction
        segments.append(
            f"BHT{self.element_separator}"
            f"0022{self.element_separator}"  # Hierarchical Structure Code
            f"13{self.element_separator}"  # Transaction Set Purpose Code
            f"ELI{self.generate_control_number()}{self.element_separator}"  # Reference Identification
            f"{self.generate_date()}{self.element_separator}"  # Date
            f"{self.generate_time()}{self.segment_terminator}"  # Time
        )
        
        # HL - Hierarchical Level (Information Source)
        segments.append(
            f"HL{self.element_separator}"
            f"1{self.element_separator}"  # Hierarchical ID Number
            f"{self.element_separator}"  # Hierarchical Parent ID Number
            f"20{self.element_separator}"  # Hierarchical Level Code
            f"1{self.segment_terminator}"  # Hierarchical Child Code
        )
        
        return segments
    
    def generate_complete_transaction(self, transaction_type: str, 
                                    sender_id: str = "SENDER01", 
                                    receiver_id: str = "RECEIVER01") -> str:
        """Generate a complete X12 transaction file."""
        segments = []
        
        # ISA Header
        segments.append(self.generate_isa_header(sender_id, receiver_id))
        
        # Determine functional code based on transaction type
        functional_codes = {
            "837": "HC",  # Health Care Claim
            "835": "HP",  # Health Care Claim Payment
            "834": "BE",  # Benefit Enrollment
            "270": "HS",  # Health Services
            "271": "HS",  # Health Services
            "276": "HR",  # Health Care Status Request
            "277": "HR",  # Health Care Status Response
            "278": "HN",  # Health Care Services Review
            "279": "HN"   # Health Care Services Review
        }
        
        functional_code = functional_codes.get(transaction_type, "HC")
        
        # GS Header
        segments.append(self.generate_gs_header(functional_code, sender_id, receiver_id))
        
        # ST Header
        st_segment, st_control_number = self.generate_st_header(transaction_type)
        segments.append(st_segment)
        
        # Transaction-specific segments
        if transaction_type == "837":
            segments.extend(self.generate_837_claim())
        elif transaction_type == "835":
            segments.extend(self.generate_835_payment())
        elif transaction_type == "270":
            segments.extend(self.generate_270_eligibility_inquiry())
        # Add more transaction types as needed
        
        # SE Trailer
        segment_count = len(segments) + 1  # +1 for the SE segment itself
        segments.append(
            f"SE{self.element_separator}"
            f"{segment_count}{self.element_separator}"  # Number of Included Segments
            f"{st_control_number}{self.segment_terminator}"  # Transaction Set Control Number
        )
        
        # GE Trailer
        segments.append(
            f"GE{self.element_separator}"
            f"1{self.element_separator}"  # Number of Transaction Sets Included
            f"{self.generate_control_number()}{self.segment_terminator}"  # Group Control Number
        )
        
        # IEA Trailer
        segments.append(
            f"IEA{self.element_separator}"
            f"1{self.element_separator}"  # Number of Included Functional Groups
            f"{self.generate_control_number()}{self.segment_terminator}"  # Interchange Control Number
        )
        
        return "".join(segments)
    
    def generate_test_files(self, output_dir: str = "test_data", 
                           file_count: int = 10) -> List[str]:
        """Generate multiple test X12 files."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        generated_files = []
        transaction_types = ["837", "835", "270", "271", "276", "277"]
        
        for i in range(file_count):
            transaction_type = random.choice(transaction_types)
            
            # Generate file content
            content = self.generate_complete_transaction(transaction_type)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_x12_{transaction_type}_{timestamp}_{i:03d}.x12"
            filepath = os.path.join(output_dir, filename)
            
            # Write file
            with open(filepath, 'w', encoding='ascii') as f:
                f.write(content)
            
            generated_files.append(filepath)
            print(f"Generated: {filename} ({transaction_type} - {self.transaction_types[transaction_type]})")
        
        return generated_files

def main():
    """Main function to generate test data."""
    generator = X12TestDataGenerator()
    
    # Generate test files
    print("Generating X12 test data files...")
    files = generator.generate_test_files(
        output_dir="test_x12_data",
        file_count=20
    )
    
    print(f"\nGenerated {len(files)} test files in 'test_x12_data' directory")
    print("\nSupported transaction types:")
    for code, description in generator.transaction_types.items():
        print(f"  {code}: {description}")
    
    # Generate a sample configuration file
    config = {
        "test_scenarios": [
            {
                "name": "development_testing",
                "file_count": 50,
                "transaction_types": ["837", "835", "270", "271"],
                "file_size_range": "25-75KB"
            },
            {
                "name": "load_testing",
                "file_count": 1000,
                "transaction_types": ["837", "835"],
                "file_size_range": "50-100KB"
            }
        ]
    }
    
    with open("test_data_config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\nGenerated test_data_config.json with sample scenarios")

if __name__ == "__main__":
    main()
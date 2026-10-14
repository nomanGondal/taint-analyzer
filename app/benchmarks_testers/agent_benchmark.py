"""
MCP Agent Vulnerability Scanner - Benchmark and Testing Suite
This module provides comprehensive testing and benchmarking capabilities for MCP agents.
Tests all 4 benchmark agents and generates security analysis reports.
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents import BENCHMARK_AGENTS, WebScraperAgent, DatabaseQueryAgent, FileSystemAgent, ProcessExecutionAgent
from app.analyzer.scan_pipeline import run_agentic_scan
from app.utils.file_utils import _write_pyre_config_for_upload
from constants.app_constants import BENCHMARKS_DIR, REPORTS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkTestSuite:
    """
    Comprehensive test suite for MCP agent vulnerability scanning.
    Tests all 4 benchmark agents with various payloads.
    """

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().isoformat()
        self.agents = [
            ("WebScraperAgent", WebScraperAgent),
            ("DatabaseQueryAgent", DatabaseQueryAgent),
            ("FileSystemAgent", FileSystemAgent),
            ("ProcessExecutionAgent", ProcessExecutionAgent),
        ]

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive tests on all benchmark agents.
        """
        logger.info("=" * 60)
        logger.info("Starting MCP Agent Vulnerability Scan - Full Benchmark")
        logger.info("=" * 60)
        
        summary = {
            "timestamp": self.timestamp,
            "total_agents": len(self.agents),
            "agents_tested": [],
            "total_vulnerabilities_found": 0,
            "vulnerability_breakdown": {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
            },
        }
        
        for agent_name, agent_class in self.agents:
            logger.info("\n" + "=" * 60)
            logger.info(f"Testing Agent: {agent_name}")
            logger.info("=" * 60)
            
            result = self._test_single_agent(agent_name, agent_class)
            self.results[agent_name] = result
            summary["agents_tested"].append(result)
            
            # Update summary
            summary["total_vulnerabilities_found"] += result.get("total_issues", 0)
            for severity in ["HIGH", "MEDIUM", "LOW"]:
                summary["vulnerability_breakdown"][severity] += result.get("summary", {}).get(severity, 0)
        
        logger.info("\n" + "=" * 60)
        logger.info("SCAN COMPLETE - Summary")
        logger.info("=" * 60)
        logger.info(f"Total Agents Scanned: {summary['total_agents']}")
        logger.info(f"Total Vulnerabilities Found: {summary['total_vulnerabilities_found']}")
        logger.info(f"  - HIGH: {summary['vulnerability_breakdown']['HIGH']}")
        logger.info(f"  - MEDIUM: {summary['vulnerability_breakdown']['MEDIUM']}")
        logger.info(f"  - LOW: {summary['vulnerability_breakdown']['LOW']}")
        logger.info("=" * 60)
        
        return summary

    def _test_single_agent(self, agent_name: str, agent_class) -> Dict[str, Any]:
        """
        Test a single agent by extracting and scanning its source code.
        """
        import uuid
        import inspect
        import os
        
        try:
            project_id = f"benchmark_{agent_name}_{uuid.uuid4().hex[:8]}"
            upload_folder = f"{BENCHMARKS_DIR}/{project_id}"
            os.makedirs(upload_folder, exist_ok=True)
            
            # Extract source code
            source_code = inspect.getsource(agent_class)
            agent_file = os.path.join(upload_folder, f"{agent_name.lower()}_agent.py")
            
            with open(agent_file, "w") as f:
                f.write(source_code)
            
            logger.info(f"Agent source saved: {agent_file}")
            logger.info(f"Source code size: {len(source_code)} bytes")
            
            # Write Pyre configuration
            _write_pyre_config_for_upload(upload_folder)
            
            # Run security analysis pipeline
            logger.info("Running security analysis pipeline...")
            scan_result = run_agentic_scan(upload_folder, project_id)
            
            # Extract summary
            result = {
                "agent_name": agent_name,
                "project_id": project_id,
                "total_issues": scan_result.get("issues_count", 0),
                "summary": scan_result.get("summary", {}),
                "pipeline": scan_result.get("pipeline", {}),
                "issues_count": {
                    "mcp_issues": scan_result.get("summary", {}).get("mcp_issues", 0),
                    "pyre_issues": scan_result.get("summary", {}).get("pyre_issues", 0),
                    "pysa_issues": scan_result.get("summary", {}).get("pysa_issues", 0),
                },
            }
            
            logger.info(f"Agent scan complete:")
            logger.info(f"  - Total Issues: {result['total_issues']}")
            logger.info(f"  - MCP Issues: {result['issues_count']['mcp_issues']}")
            logger.info(f"  - Pyre Issues: {result['issues_count']['pyre_issues']}")
            logger.info(f"  - Pysa Issues: {result['issues_count']['pysa_issues']}")
            
            if result['total_issues'] > 0:
                summary = scan_result.get("summary", {})
                logger.info(f"  - HIGH: {summary.get('high', 0)}")
                logger.info(f"  - MEDIUM: {summary.get('medium', 0)}")
                logger.info(f"  - LOW: {summary.get('low', 0)}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error testing {agent_name}: {str(e)}", exc_info=True)
            return {
                "agent_name": agent_name,
                "error": str(e),
                "total_issues": 0,
            }

    def save_results(self, output_file: str = None) -> str:
        """
        Save test results to a JSON file.
        """
        if output_file is None:
            output_file = f"{REPORTS_DIR}/benchmark_results_{self.timestamp.replace(':', '-')}.json"
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        return output_file

    def generate_report(self) -> str:
        """
        Generate a human-readable report of the benchmark results.
        """
        import os
        
        report = []
        report.append("=" * 80)
        report.append("MCP AGENT VULNERABILITY SCANNER - BENCHMARK REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.timestamp}")
        report.append("")
        
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 80)
        
        total_agents = len(self.results)
        total_issues = sum(r.get("total_issues", 0) for r in self.results.values())
        
        report.append(f"Total Agents Analyzed: {total_agents}")
        report.append(f"Total Vulnerabilities Found: {total_issues}")
        report.append("")
        
        report.append("DETAILED RESULTS")
        report.append("-" * 80)
        
        for agent_name, result in self.results.items():
            report.append(f"\nAgent: {agent_name}")
            report.append(f"  Project ID: {result.get('project_id', 'N/A')}")
            report.append(f"  Total Issues: {result.get('total_issues', 0)}")
            
            if "error" in result:
                report.append(f"  Error: {result['error']}")
            else:
                issues_count = result.get("issues_count", {})
                report.append(f"  - MCP Issues: {issues_count.get('mcp_issues', 0)}")
                report.append(f"  - Pyre Issues: {issues_count.get('pyre_issues', 0)}")
                report.append(f"  - Pysa Issues: {issues_count.get('pysa_issues', 0)}")
                
                summary = result.get("summary", {})
                if summary:
                    report.append(f"  Severity Breakdown:")
                    report.append(f"    - HIGH: {summary.get('high', 0)}")
                    report.append(f"    - MEDIUM: {summary.get('medium', 0)}")
                    report.append(f"    - LOW: {summary.get('low', 0)}")
        
        report.append("\n" + "=" * 80)
        report.append("VULNERABILITY TYPES")
        report.append("-" * 80)
        
        report.append("\n1. WebScraperAgent Vulnerabilities:")
        report.append("   - SSRF (Server-Side Request Forgery)")
        report.append("   - Command Injection")
        report.append("   - Insecure Deserialization (pickle)")
        report.append("   - Hardcoded Secrets")
        
        report.append("\n2. DatabaseQueryAgent Vulnerabilities:")
        report.append("   - SQL Injection")
        report.append("   - LDAP Injection")
        report.append("   - Information Disclosure")
        report.append("   - Path Traversal in Backups")
        
        report.append("\n3. FileSystemAgent Vulnerabilities:")
        report.append("   - Path Traversal / Directory Traversal")
        report.append("   - Arbitrary File Read/Write/Delete")
        report.append("   - Unsafe Symlink Operations")
        report.append("   - Zip Slip Attack")
        
        report.append("\n4. ProcessExecutionAgent Vulnerabilities:")
        report.append("   - Command Injection via shell=True")
        report.append("   - Code Execution (eval/exec)")
        report.append("   - Environment Variable Injection")
        report.append("   - Argument Injection")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


def main():
    """
    Main entry point for the benchmark test suite.
    """
    import os
    
    # Ensure directories exist
    os.makedirs(BENCHMARKS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Create and run test suite
    suite = BenchmarkTestSuite()
    suite.run_all_tests()
    
    # Save results
    results_file = suite.save_results()
    logger.info(f"Results saved to: {results_file}")
    
    # Generate and print report
    report = suite.generate_report()
    print("\n" + report)
    
    # Save report
    report_file = f"{REPORTS_DIR}/benchmark_report_{suite.timestamp.replace(':', '-')}.txt"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w") as f:
        f.write(report)
    logger.info(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()

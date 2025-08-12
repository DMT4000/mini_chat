"""
Workflow analytics and performance tracking for the AI Co-founder agent.

This module implements the WorkflowAnalytics class that tracks execution metrics,
efficiency gains, and provides A/B testing capabilities for workflow optimization.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
analytics_logger = logging.getLogger(__name__)


class WorkflowAnalytics:
    """
    Analytics system for tracking and optimizing workflow performance.
    
    This class provides:
    - Detailed timing metrics for each node and workflow path
    - Efficiency scoring based on time, accuracy, and user satisfaction
    - A/B testing framework for workflow variations
    - Performance monitoring and alerting
    """
    
    def __init__(self, max_history_size: int = 1000):
        """
        Initialize the workflow analytics system.
        
        Args:
            max_history_size: Maximum number of execution records to keep in memory
        """
        self.max_history_size = max_history_size
        self.execution_history = deque(maxlen=max_history_size)
        self.node_metrics = defaultdict(list)
        self.path_metrics = defaultdict(list)
        self.ab_test_results = {}
        self.performance_baselines = {}
        
        # Efficiency tracking
        self.efficiency_metrics = {
            'total_executions': 0,
            'lightweight_path_count': 0,
            'full_workflow_count': 0,
            'fact_extraction_skipped': 0,
            'fact_extraction_performed': 0,
            'average_response_time': 0.0,
            'api_calls_saved': 0
        }
        
        print("📊 Workflow analytics system initialized")
    
    def track_execution_metrics(self, user_id: str, workflow_path: str, 
                              execution_time: float, success: bool,
                              node_timings: Dict[str, float] = None,
                              additional_metrics: Dict[str, Any] = None):
        """
        Track detailed execution metrics for a workflow run.
        
        Args:
            user_id: User identifier
            workflow_path: Path taken through workflow (e.g., "lightweight", "full")
            execution_time: Total execution time in seconds
            success: Whether execution was successful
            node_timings: Dictionary of node name -> execution time
            additional_metrics: Additional custom metrics
        """
        try:
            # Create execution record
            execution_record = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'workflow_path': workflow_path,
                'execution_time': execution_time,
                'success': success,
                'node_timings': node_timings or {},
                'additional_metrics': additional_metrics or {}
            }
            
            # Add to history
            self.execution_history.append(execution_record)
            
            # Update path metrics
            self.path_metrics[workflow_path].append({
                'execution_time': execution_time,
                'success': success,
                'timestamp': datetime.now()
            })
            
            # Update node metrics
            if node_timings:
                for node_name, timing in node_timings.items():
                    self.node_metrics[node_name].append({
                        'execution_time': timing,
                        'success': success,
                        'timestamp': datetime.now()
                    })
            
            # Update efficiency metrics
            self._update_efficiency_metrics(workflow_path, execution_time, success)
            
            analytics_logger.info(f"Tracked execution: {workflow_path} in {execution_time:.2f}s")
            
        except Exception as e:
            analytics_logger.error(f"Error tracking execution metrics: {str(e)}")
    
    def _update_efficiency_metrics(self, workflow_path: str, execution_time: float, success: bool):
        """Update overall efficiency metrics."""
        self.efficiency_metrics['total_executions'] += 1
        
        if workflow_path == 'lightweight':
            self.efficiency_metrics['lightweight_path_count'] += 1
            # Estimate API calls saved (lightweight path saves ~3-4 API calls)
            self.efficiency_metrics['api_calls_saved'] += 3
        elif workflow_path == 'full':
            self.efficiency_metrics['full_workflow_count'] += 1
        
        # Update average response time
        total_time = (self.efficiency_metrics['average_response_time'] * 
                     (self.efficiency_metrics['total_executions'] - 1) + execution_time)
        self.efficiency_metrics['average_response_time'] = total_time / self.efficiency_metrics['total_executions']
    
    def track_fact_extraction_decision(self, user_id: str, decision: str, 
                                     conversation_length: int, facts_found: int = 0):
        """
        Track fact extraction decisions for efficiency analysis.
        
        Args:
            user_id: User identifier
            decision: "performed" or "skipped"
            conversation_length: Length of conversation text
            facts_found: Number of facts extracted (if performed)
        """
        try:
            if decision == 'skipped':
                self.efficiency_metrics['fact_extraction_skipped'] += 1
                # Estimate API calls saved (fact extraction saves ~2 API calls)
                self.efficiency_metrics['api_calls_saved'] += 2
            elif decision == 'performed':
                self.efficiency_metrics['fact_extraction_performed'] += 1
            
            # Track decision record
            decision_record = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'decision': decision,
                'conversation_length': conversation_length,
                'facts_found': facts_found
            }
            
            # Add to execution history with special marker
            decision_record['type'] = 'fact_extraction_decision'
            self.execution_history.append(decision_record)
            
            analytics_logger.info(f"Tracked fact extraction decision: {decision} for user {user_id}")
            
        except Exception as e:
            analytics_logger.error(f"Error tracking fact extraction decision: {str(e)}")
    
    def calculate_efficiency_score(self, time_weight: float = 0.4, 
                                 accuracy_weight: float = 0.4,
                                 satisfaction_weight: float = 0.2) -> float:
        """
        Calculate overall workflow efficiency score.
        
        Args:
            time_weight: Weight for response time component
            accuracy_weight: Weight for accuracy component  
            satisfaction_weight: Weight for user satisfaction component
            
        Returns:
            float: Efficiency score between 0.0 and 1.0
        """
        try:
            if self.efficiency_metrics['total_executions'] == 0:
                return 0.0
            
            # Time efficiency (lower is better, normalize to 0-1)
            avg_time = self.efficiency_metrics['average_response_time']
            time_score = max(0.0, 1.0 - (avg_time / 10.0))  # Assume 10s is poor performance
            
            # Accuracy efficiency (success rate) — only count execution records
            execution_records = [r for r in self.execution_history if 'success' in r]
            successful_executions = sum(1 for record in execution_records if record.get('success', False))
            accuracy_score = (successful_executions / len(execution_records)) if execution_records else 0.0
            
            # Satisfaction efficiency (proxy: lightweight path usage)
            total_paths = (self.efficiency_metrics['lightweight_path_count'] + 
                          self.efficiency_metrics['full_workflow_count'])
            satisfaction_score = (self.efficiency_metrics['lightweight_path_count'] / total_paths 
                                if total_paths > 0 else 0.0)
            
            # Calculate weighted score
            efficiency_score = (time_weight * time_score + 
                              accuracy_weight * accuracy_score + 
                              satisfaction_weight * satisfaction_score)
            
            return min(1.0, max(0.0, efficiency_score))
            
        except Exception as e:
            analytics_logger.error(f"Error calculating efficiency score: {str(e)}")
            return 0.0
    
    def run_ab_test(self, test_name: str, variant_a: str, variant_b: str, 
                   user_id: str, metric_name: str = 'execution_time') -> Dict[str, Any]:
        """
        Execute A/B test for workflow variations.
        
        Args:
            test_name: Name of the A/B test
            variant_a: Name of variant A
            variant_b: Name of variant B
            user_id: User identifier for test assignment
            metric_name: Metric to compare between variants
            
        Returns:
            Dict containing test results and recommendations
        """
        try:
            # Initialize test if not exists
            if test_name not in self.ab_test_results:
                self.ab_test_results[test_name] = {
                    'variant_a': variant_a,
                    'variant_b': variant_b,
                    'results_a': [],
                    'results_b': [],
                    'assignments': {},
                    'start_time': datetime.now().isoformat()
                }
            
            test_data = self.ab_test_results[test_name]
            
            # Assign user to variant (simple hash-based assignment)
            if user_id not in test_data['assignments']:
                # Simple assignment based on user_id hash
                variant = variant_a if hash(user_id) % 2 == 0 else variant_b
                test_data['assignments'][user_id] = variant
            
            assigned_variant = test_data['assignments'][user_id]
            
            # Return test assignment info
            return {
                'test_name': test_name,
                'assigned_variant': assigned_variant,
                'total_assignments_a': sum(1 for v in test_data['assignments'].values() if v == variant_a),
                'total_assignments_b': sum(1 for v in test_data['assignments'].values() if v == variant_b)
            }
            
        except Exception as e:
            analytics_logger.error(f"Error running A/B test: {str(e)}")
            return {'error': str(e)}
    
    def analyze_ab_test_results(self, test_name: str) -> Dict[str, Any]:
        """
        Analyze results of an A/B test.
        
        Args:
            test_name: Name of the A/B test to analyze
            
        Returns:
            Dict containing statistical analysis of test results
        """
        try:
            if test_name not in self.ab_test_results:
                return {'error': f'Test {test_name} not found'}
            
            test_data = self.ab_test_results[test_name]
            
            # Calculate basic statistics
            results_a = test_data['results_a']
            results_b = test_data['results_b']
            
            if not results_a or not results_b:
                return {'error': 'Insufficient data for analysis'}
            
            avg_a = sum(results_a) / len(results_a)
            avg_b = sum(results_b) / len(results_b)
            
            # Determine winner
            winner = test_data['variant_a'] if avg_a < avg_b else test_data['variant_b']
            improvement = abs(avg_a - avg_b) / max(avg_a, avg_b) * 100
            
            return {
                'test_name': test_name,
                'variant_a': test_data['variant_a'],
                'variant_b': test_data['variant_b'],
                'sample_size_a': len(results_a),
                'sample_size_b': len(results_b),
                'average_a': avg_a,
                'average_b': avg_b,
                'winner': winner,
                'improvement_percentage': improvement,
                'confidence': 'medium' if min(len(results_a), len(results_b)) > 10 else 'low'
            }
            
        except Exception as e:
            analytics_logger.error(f"Error analyzing A/B test results: {str(e)}")
            return {'error': str(e)}
    
    def get_performance_summary(self, time_period_hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for a specified time period.
        
        Args:
            time_period_hours: Hours to look back for metrics
            
        Returns:
            Dict containing performance summary
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_period_hours)
            
            # Filter recent executions
            recent_executions = [
                record for record in self.execution_history
                if datetime.fromisoformat(record['timestamp']) > cutoff_time
                and record.get('type') != 'fact_extraction_decision'
            ]
            
            if not recent_executions:
                return {'message': 'No executions in specified time period'}
            
            # Calculate metrics
            total_executions = len(recent_executions)
            successful_executions = sum(1 for r in recent_executions if r.get('success', False))
            avg_execution_time = sum(r['execution_time'] for r in recent_executions) / total_executions
            
            # Path distribution
            path_counts = defaultdict(int)
            for record in recent_executions:
                path_counts[record['workflow_path']] += 1
            
            # Efficiency gains
            lightweight_count = path_counts.get('lightweight', 0)
            efficiency_percentage = (lightweight_count / total_executions * 100) if total_executions > 0 else 0
            
            return {
                'time_period_hours': time_period_hours,
                'total_executions': total_executions,
                'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
                'average_execution_time': avg_execution_time,
                'path_distribution': dict(path_counts),
                'efficiency_percentage': efficiency_percentage,
                'api_calls_saved_estimate': self.efficiency_metrics['api_calls_saved'],
                'efficiency_score': self.calculate_efficiency_score()
            }
            
        except Exception as e:
            analytics_logger.error(f"Error generating performance summary: {str(e)}")
            return {'error': str(e)}
    
    def detect_performance_degradation(self, threshold_percentage: float = 20.0) -> Dict[str, Any]:
        """
        Detect performance degradation by comparing recent metrics to baseline.
        
        Args:
            threshold_percentage: Percentage degradation threshold for alerting
            
        Returns:
            Dict containing degradation analysis and alerts
        """
        try:
            # Get recent performance (last hour)
            recent_summary = self.get_performance_summary(time_period_hours=1)
            
            if 'error' in recent_summary:
                return recent_summary
            
            # Compare to baseline (last 24 hours)
            baseline_summary = self.get_performance_summary(time_period_hours=24)
            
            if 'error' in baseline_summary:
                return {'message': 'Insufficient baseline data'}
            
            # Calculate degradation
            recent_time = recent_summary.get('average_execution_time', 0)
            baseline_time = baseline_summary.get('average_execution_time', 0)
            
            if baseline_time == 0:
                return {'message': 'No baseline data available'}
            
            time_degradation = ((recent_time - baseline_time) / baseline_time) * 100
            
            recent_success = recent_summary.get('success_rate', 0)
            baseline_success = baseline_summary.get('success_rate', 0)
            
            success_degradation = baseline_success - recent_success
            
            # Check for alerts
            alerts = []
            if time_degradation > threshold_percentage:
                alerts.append(f"Response time degraded by {time_degradation:.1f}%")
            
            if success_degradation > threshold_percentage:
                alerts.append(f"Success rate degraded by {success_degradation:.1f}%")
            
            return {
                'time_degradation_percentage': time_degradation,
                'success_degradation_percentage': success_degradation,
                'alerts': alerts,
                'requires_attention': len(alerts) > 0,
                'recent_metrics': recent_summary,
                'baseline_metrics': baseline_summary
            }
            
        except Exception as e:
            analytics_logger.error(f"Error detecting performance degradation: {str(e)}")
            return {'error': str(e)}
    
    def export_analytics_data(self) -> Dict[str, Any]:
        """
        Export all analytics data for external analysis.
        
        Returns:
            Dict containing all analytics data
        """
        try:
            return {
                'execution_history': list(self.execution_history),
                'efficiency_metrics': self.efficiency_metrics,
                'ab_test_results': self.ab_test_results,
                'performance_baselines': self.performance_baselines,
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            analytics_logger.error(f"Error exporting analytics data: {str(e)}")
            return {'error': str(e)}
    
    def reset_analytics(self):
        """Reset all analytics data."""
        self.execution_history.clear()
        self.node_metrics.clear()
        self.path_metrics.clear()
        self.ab_test_results.clear()
        self.performance_baselines.clear()
        
        self.efficiency_metrics = {
            'total_executions': 0,
            'lightweight_path_count': 0,
            'full_workflow_count': 0,
            'fact_extraction_skipped': 0,
            'fact_extraction_performed': 0,
            'average_response_time': 0.0,
            'api_calls_saved': 0
        }
        
        analytics_logger.info("Analytics data reset")


# Export the main class
__all__ = ["WorkflowAnalytics"]
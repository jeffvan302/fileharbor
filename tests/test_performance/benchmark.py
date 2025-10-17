"""
Performance Benchmarks for FileHarbor

Measures transfer throughput, concurrent connections, and resource usage.
"""

import time
import tempfile
import threading
from pathlib import Path
import statistics

from fileharbor import FileHarborServer, FileHarborClient
from fileharbor.common.config_schema import ServerConfig, ClientConfig


class PerformanceBenchmark:
    """Performance benchmarking suite for FileHarbor."""
    
    def __init__(self, server_config: ServerConfig, client_config: ClientConfig):
        """
        Initialize benchmark.
        
        Args:
            server_config: Server configuration
            client_config: Client configuration
        """
        self.server_config = server_config
        self.client_config = client_config
        self.server = None
        self.server_thread = None
    
    def start_server(self):
        """Start server in background thread."""
        self.server = FileHarborServer(self.server_config)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        time.sleep(1)  # Wait for startup
    
    def stop_server(self):
        """Stop server."""
        if self.server:
            self.server.stop()
    
    def benchmark_upload_throughput(self, file_sizes_mb: list[int]) -> dict:
        """
        Benchmark upload throughput for various file sizes.
        
        Args:
            file_sizes_mb: List of file sizes in MB to test
            
        Returns:
            Dictionary with results
        """
        results = {}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            for size_mb in file_sizes_mb:
                # Create test file
                test_file = temp_dir / f"test_{size_mb}mb.bin"
                size_bytes = size_mb * 1024 * 1024
                test_file.write_bytes(b"X" * size_bytes)
                
                # Measure upload time
                with FileHarborClient(self.client_config) as client:
                    start_time = time.time()
                    client.upload(str(test_file), f"test_{size_mb}mb.bin")
                    elapsed = time.time() - start_time
                
                # Calculate throughput
                throughput_mbps = (size_mb * 8) / elapsed  # Megabits per second
                
                results[f"{size_mb}MB"] = {
                    'elapsed_seconds': elapsed,
                    'throughput_mbps': throughput_mbps,
                    'throughput_MBps': size_mb / elapsed
                }
                
                print(f"Upload {size_mb}MB: {elapsed:.2f}s @ {throughput_mbps:.2f} Mbps")
        
        return results
    
    def benchmark_download_throughput(self, file_sizes_mb: list[int]) -> dict:
        """
        Benchmark download throughput for various file sizes.
        
        Args:
            file_sizes_mb: List of file sizes in MB to test
            
        Returns:
            Dictionary with results
        """
        results = {}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # First upload files
            with FileHarborClient(self.client_config) as client:
                for size_mb in file_sizes_mb:
                    test_file = temp_dir / f"download_test_{size_mb}mb.bin"
                    size_bytes = size_mb * 1024 * 1024
                    test_file.write_bytes(b"Y" * size_bytes)
                    client.upload(str(test_file), f"download_test_{size_mb}mb.bin")
            
            # Now benchmark downloads
            for size_mb in file_sizes_mb:
                download_file = temp_dir / f"downloaded_{size_mb}mb.bin"
                
                with FileHarborClient(self.client_config) as client:
                    start_time = time.time()
                    client.download(f"download_test_{size_mb}mb.bin", str(download_file))
                    elapsed = time.time() - start_time
                
                throughput_mbps = (size_mb * 8) / elapsed
                
                results[f"{size_mb}MB"] = {
                    'elapsed_seconds': elapsed,
                    'throughput_mbps': throughput_mbps,
                    'throughput_MBps': size_mb / elapsed
                }
                
                print(f"Download {size_mb}MB: {elapsed:.2f}s @ {throughput_mbps:.2f} Mbps")
        
        return results
    
    def benchmark_small_files(self, num_files: int = 100) -> dict:
        """
        Benchmark transfer of many small files.
        
        Args:
            num_files: Number of small files to transfer
            
        Returns:
            Dictionary with results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create small files
            for i in range(num_files):
                file = temp_dir / f"small_{i}.txt"
                file.write_text(f"Small file {i}")
            
            # Benchmark upload
            with FileHarborClient(self.client_config) as client:
                start_time = time.time()
                
                for i in range(num_files):
                    client.upload(
                        str(temp_dir / f"small_{i}.txt"),
                        f"small_{i}.txt"
                    )
                
                elapsed = time.time() - start_time
            
            files_per_second = num_files / elapsed
            
            result = {
                'num_files': num_files,
                'elapsed_seconds': elapsed,
                'files_per_second': files_per_second
            }
            
            print(f"Small files: {num_files} files in {elapsed:.2f}s ({files_per_second:.1f} files/sec)")
            
            return result
    
    def benchmark_concurrent_clients(self, num_clients: int = 3) -> dict:
        """
        Benchmark concurrent client connections.
        
        Note: With library mutex, only one client can operate at a time,
        but this tests connection handling.
        
        Args:
            num_clients: Number of concurrent clients
            
        Returns:
            Dictionary with results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create test files for each client
            for i in range(num_clients):
                file = temp_dir / f"concurrent_{i}.txt"
                file.write_text(f"Concurrent client {i}")
            
            def client_task(client_id):
                """Task for each client thread."""
                with FileHarborClient(self.client_config) as client:
                    client.upload(
                        str(temp_dir / f"concurrent_{client_id}.txt"),
                        f"concurrent_{client_id}.txt"
                    )
            
            # Run clients concurrently
            start_time = time.time()
            
            threads = []
            for i in range(num_clients):
                thread = threading.Thread(target=client_task, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            elapsed = time.time() - start_time
            
            result = {
                'num_clients': num_clients,
                'elapsed_seconds': elapsed,
                'avg_time_per_client': elapsed / num_clients
            }
            
            print(f"Concurrent: {num_clients} clients in {elapsed:.2f}s (avg {result['avg_time_per_client']:.2f}s)")
            
            return result
    
    def benchmark_resume_overhead(self, file_size_mb: int = 10) -> dict:
        """
        Measure overhead of resumable transfers vs non-resumable.
        
        Args:
            file_size_mb: Size of test file
            
        Returns:
            Dictionary with results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create test file
            test_file = temp_dir / f"resume_test.bin"
            size_bytes = file_size_mb * 1024 * 1024
            test_file.write_bytes(b"Z" * size_bytes)
            
            times = {'resume': [], 'no_resume': []}
            
            # Test with resume enabled (3 runs)
            for i in range(3):
                with FileHarborClient(self.client_config) as client:
                    start = time.time()
                    client.upload(str(test_file), f"resume_test_{i}.bin", resume=True)
                    times['resume'].append(time.time() - start)
            
            # Test without resume (3 runs)
            for i in range(3):
                with FileHarborClient(self.client_config) as client:
                    start = time.time()
                    client.upload(str(test_file), f"noresume_test_{i}.bin", resume=False)
                    times['no_resume'].append(time.time() - start)
            
            result = {
                'file_size_mb': file_size_mb,
                'resume_avg': statistics.mean(times['resume']),
                'no_resume_avg': statistics.mean(times['no_resume']),
                'overhead_percent': (
                    (statistics.mean(times['resume']) - statistics.mean(times['no_resume']))
                    / statistics.mean(times['no_resume']) * 100
                )
            }
            
            print(f"Resume overhead: {result['overhead_percent']:.1f}%")
            
            return result
    
    def run_all_benchmarks(self) -> dict:
        """
        Run all benchmarks and return comprehensive results.
        
        Returns:
            Dictionary with all benchmark results
        """
        print("=" * 60)
        print("FileHarbor Performance Benchmarks")
        print("=" * 60)
        print()
        
        self.start_server()
        
        try:
            results = {}
            
            print("1. Upload Throughput")
            print("-" * 40)
            results['upload'] = self.benchmark_upload_throughput([1, 5, 10])
            print()
            
            print("2. Download Throughput")
            print("-" * 40)
            results['download'] = self.benchmark_download_throughput([1, 5, 10])
            print()
            
            print("3. Small Files")
            print("-" * 40)
            results['small_files'] = self.benchmark_small_files(50)
            print()
            
            print("4. Concurrent Clients")
            print("-" * 40)
            results['concurrent'] = self.benchmark_concurrent_clients(3)
            print()
            
            print("5. Resume Overhead")
            print("-" * 40)
            results['resume'] = self.benchmark_resume_overhead(5)
            print()
            
            print("=" * 60)
            print("Benchmarks Complete")
            print("=" * 60)
            
            return results
            
        finally:
            self.stop_server()


def print_summary(results: dict):
    """
    Print benchmark summary.
    
    Args:
        results: Benchmark results dictionary
    """
    print("\nSummary:")
    print("=" * 60)
    
    if 'upload' in results:
        print("\nUpload Throughput:")
        for size, data in results['upload'].items():
            print(f"  {size}: {data['throughput_mbps']:.1f} Mbps")
    
    if 'download' in results:
        print("\nDownload Throughput:")
        for size, data in results['download'].items():
            print(f"  {size}: {data['throughput_mbps']:.1f} Mbps")
    
    if 'small_files' in results:
        print(f"\nSmall Files: {results['small_files']['files_per_second']:.1f} files/sec")
    
    if 'concurrent' in results:
        print(f"\nConcurrent Clients: {results['concurrent']['elapsed_seconds']:.2f}s total")
    
    if 'resume' in results:
        print(f"\nResume Overhead: {results['resume']['overhead_percent']:.1f}%")


if __name__ == '__main__':
    # Run benchmarks with test config
    # (In practice, use actual server and client configs)
    print("Note: Run with actual server and client configurations")
    print("See test_integration/test_server_client.py for config examples")

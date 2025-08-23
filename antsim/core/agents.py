"""Agent factory for creating queens and workers with proper configuration."""
import logging
from typing import Dict, Any, List, Tuple, Optional

from .worker import Worker
from .queen import Queen

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating and managing agents (queens and workers)."""
    
    def __init__(self, queen_config: Optional[Dict[str, Any]] = None, 
                 worker_config: Optional[Dict[str, Any]] = None):
        """Initialize agent factory with configurations.
        
        Args:
            queen_config: Configuration for queens
            worker_config: Configuration for workers
        """
        self.queen_config = queen_config or self._default_queen_config()
        self.worker_config = worker_config or self._default_worker_config()
        
    def _default_queen_config(self) -> Dict[str, Any]:
        """Default configuration for queens."""
        return {
            "energy": 200,
            "max_energy": 200,
            "social_stomach": 150,
            "social_stomach_capacity": 150,
            "egg_laying_interval": 10,
            "max_eggs": 100,
            "hunger_threshold": 75,
        }
    
    def _default_worker_config(self) -> Dict[str, Any]:
        """Default configuration for workers."""
        return {
            "energy": 100,
            "max_energy": 100,
            "stomach_capacity": 100,
            "social_stomach_capacity": 100,
            "hunger_threshold": 50,
        }
    
    def create_queen(self, queen_id: int, position: Tuple[int, int]) -> Queen:
        """Create a new queen.
        
        Args:
            queen_id: Unique queen identifier (typically 0)
            position: Initial position (x, y)
            
        Returns:
            Queen instance
        """
        logger.info(f"Creating queen with id={queen_id} at position {position}")
        return Queen(queen_id, position, self.queen_config.copy())
    
    def create_worker(self, worker_id: int, position: Tuple[int, int]) -> Worker:
        """Create a new worker.
        
        Args:
            worker_id: Unique worker identifier
            position: Initial position (x, y)
            
        Returns:
            Worker instance
        """
        logger.info(f"Creating worker with id={worker_id} at position {position}")
        return Worker(worker_id, position, self.worker_config.copy())
    
    def create_initial_colony(self, entry_positions: List[Tuple[int, int]], 
                            queen_count: int = 1, worker_count: int = 2) -> Tuple[List[Queen], List[Worker]]:
        """Create initial colony with specified composition.
        
        Args:
            entry_positions: Available starting positions
            queen_count: Number of queens to create (default: 1)
            worker_count: Number of workers to create (default: 2)
            
        Returns:
            Tuple of (queens_list, workers_list)
        """
        if len(entry_positions) < queen_count + worker_count:
            logger.warning(f"Not enough entry positions ({len(entry_positions)}) for "
                         f"{queen_count} queens + {worker_count} workers. "
                         f"Some agents will share positions.")
        
        queens = []
        workers = []
        
        # Create queens first (they get priority positions)
        for i in range(queen_count):
            queen_id = i  # Queens get IDs 0, 1, 2, ...
            pos_idx = i % len(entry_positions)  # Wrap around if not enough positions
            position = entry_positions[pos_idx]
            queen = self.create_queen(queen_id, position)
            queens.append(queen)
        
        # Create workers (they get subsequent IDs)
        for i in range(worker_count):
            worker_id = queen_count + i  # Workers get IDs after queens
            pos_idx = (queen_count + i) % len(entry_positions)  # Wrap around if needed
            position = entry_positions[pos_idx]
            
            # If sharing position with queen, offset slightly
            if pos_idx < queen_count:
                x, y = position
                # Try to place worker adjacent to queen
                adjacent_positions = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
                for adj_pos in adjacent_positions:
                    if adj_pos not in [q.position for q in queens]:
                        position = adj_pos
                        break
            
            worker = self.create_worker(worker_id, position)
            workers.append(worker)
        
        logger.info(f"Created initial colony: {len(queens)} queens, {len(workers)} workers")
        return queens, workers
    
    def get_all_agents(self, queens: List[Queen], workers: List[Worker]) -> List[Any]:
        """Get all agents as a single list for compatibility.
        
        Args:
            queens: List of queens
            workers: List of workers
            
        Returns:
            Combined list of all agents
        """
        return queens + workers
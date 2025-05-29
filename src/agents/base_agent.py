"""
Base agent class for CrewAI agents.
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from crewai import Agent
from config.litellm_config import get_litellm_config

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents in the system."""
    
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List] = None,
        verbose: bool = True,
        max_iter: int = 5,
        memory: bool = True
    ):
        """
        Initialize base agent.
        
        Args:
            role: Agent's role/title
            goal: What the agent aims to achieve
            backstory: Agent's background and expertise
            tools: List of tools available to the agent
            verbose: Whether to log detailed output
            max_iter: Maximum iterations for task completion
            memory: Whether to use memory for context
        """
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.verbose = verbose
        self.max_iter = max_iter
        self.memory = memory
        
        # Get LiteLLM configuration
        self.llm_config = get_litellm_config()
        
        # Create CrewAI agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized {self.__class__.__name__} with role: {role}")
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent instance."""
        return Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            tools=self.tools,
            verbose=self.verbose,
            max_iter=self.max_iter,
            memory=self.memory,
            llm=self._get_llm_function()
        )
    
    def _get_llm_function(self):
        """Get LLM function wrapper for CrewAI."""
        def llm_wrapper(prompt: str) -> str:
            """Wrapper to use LiteLLM with CrewAI."""
            try:
                messages = [
                    {"role": "system", "content": self.backstory},
                    {"role": "user", "content": prompt}
                ]
                
                response = self.llm_config.complete(
                    messages=messages,
                    temperature=self.get_temperature(),
                    max_tokens=self.get_max_tokens()
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"LLM error in {self.role}: {e}")
                return f"Error: Unable to process request - {str(e)}"
        
        return llm_wrapper
    
    @abstractmethod
    def get_temperature(self) -> float:
        """Get temperature setting for this agent."""
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        """Get max tokens setting for this agent."""
        pass
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent task with given context.
        
        Args:
            context: Input context for the agent
            
        Returns:
            Agent output dictionary
        """
        try:
            result = self.process(context)
            logger.info(f"{self.role} completed task successfully")
            return {
                "status": "success",
                "agent": self.role,
                "output": result
            }
        except Exception as e:
            logger.error(f"{self.role} failed: {e}")
            return {
                "status": "error",
                "agent": self.role,
                "error": str(e)
            }
    
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Any:
        """
        Process the task with given context.
        Must be implemented by subclasses.
        
        Args:
            context: Input context
            
        Returns:
            Processing result
        """
        pass
    
    def validate_output(self, output: Any) -> bool:
        """
        Validate agent output.
        Can be overridden by subclasses for specific validation.
        
        Args:
            output: Agent output to validate
            
        Returns:
            True if valid, False otherwise
        """
        return output is not None
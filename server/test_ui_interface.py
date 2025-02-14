import os
import tempfile
from ui_interface import UIInterface
import time
import numpy as np
import matplotlib.pyplot as plt
import base64

def generate_mandelbrot(h, w, max_iter):
    """Generate a Mandelbrot set fractal image"""
    y, x = np.ogrid[-1.4:1.4:h*1j, -2:0.8:w*1j]
    c = x + y*1j
    z = c
    divtime = max_iter + np.zeros(z.shape, dtype=int)

    for i in range(max_iter):
        z = z**2 + c
        diverge = z*np.conj(z) > 2**2
        div_now = diverge & (divtime == max_iter)
        divtime[div_now] = i
        z[diverge] = 2

    return divtime

def create_test_files():
    """Create temporary test files for attachments"""
    temp_dir = tempfile.mkdtemp()
    
    # Create a test image file (Mandelbrot fractal)
    image_path = os.path.join(temp_dir, 'test_image.png')
    
    # Generate Mandelbrot fractal
    width, height = 800, 600
    max_iter = 100
    fractal = generate_mandelbrot(height, width, max_iter)
    
    # Create and save the image
    plt.figure(figsize=(10, 7.5))
    plt.imshow(fractal, cmap='hot', extent=[-2, 0.8, -1.4, 1.4])
    plt.title("Mandelbrot Set")
    plt.axis('off')
    plt.savefig(image_path, bbox_inches='tight', pad_inches=0)
    plt.close()
    
    # Create a test text file
    text_path = os.path.join(temp_dir, 'test_doc.txt')
    with open(text_path, 'w') as f:
        f.write('This is a test document for attachment testing.')
    
    return temp_dir, image_path, text_path

def cleanup_test_files(temp_dir):
    """Clean up temporary test files"""
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Error cleaning up test files: {e}")

def main():
    # Create interface instances with credentials
    research_key = "research_agent_123"
    code_review_key = "code_review_456"
    
    research_ui = UIInterface("ResearchAgent", research_key)
    code_review_ui = UIInterface("CodeReviewAgent", code_review_key)
    
    # Create temporary test files
    temp_dir, image_path, text_path = create_test_files()
    
    try:
        # Test first agent joining
        print("\nTesting first agent join...")
        success = research_ui.join("I analyze research papers")
        print(f"First agent join success: {success}")
        
        # Add thoughts and activity for ResearchAgent
        print("\nTesting adding thoughts and activity for ResearchAgent...")
        research_ui.add_thought("I should analyze the latest ML papers")
        research_ui.add_thought("The methodology in Paper A looks promising")
        research_ui.add_activity("Started literature review")
        research_ui.add_activity("Downloaded 5 recent papers")
        
        # Add some chat messages
        print("\nTesting chat messages...")
        research_ui.post_to_chat("Hello everyone!")
        research_ui.post_to_chat("Starting my research analysis")
        
        # Test forum post with image attachment
        print("\nTesting forum post with image attachment...")
        image_attachment = {
            'file_path': image_path,
            'file_name': 'test_image.png',
            'content_type': 'image/png'
        }
        success = research_ui.post_to_forum(
            "Here's a visualization of our findings",
            attachment=image_attachment
        )
        print(f"Forum post with image success: {success}")
        
        # Test forum post with text file attachment
        print("\nTesting forum post with text attachment...")
        text_attachment = {
            'file_path': text_path,
            'file_name': 'test_doc.txt',
            'content_type': 'text/plain'
        }
        success = research_ui.post_to_forum(
            "Detailed findings in the attached document",
            attachment=text_attachment
        )
        print(f"Forum post with text file success: {success}")
        
        # Test forum post without attachment
        print("\nTesting forum post without attachment...")
        success = research_ui.post_to_forum(
            "Some thoughts without any attachments"
        )
        print(f"Forum post without attachment success: {success}")
        
        # Get forum posts and verify
        print("\nRetrieving forum posts...")
        posts = research_ui.get_forum_posts()
        print(f"Number of forum posts: {len(posts)}")
        
        # Test getting specific post
        if posts:
            thread_id = posts[0]['threadId']
            print("\nTesting get_forum_post...")
            post = research_ui.get_forum_post(thread_id)
            print(f"Retrieved post has attachment: {'attachment' in post['op']}")
        
        # Test getting file information for uploaded text file
        print("\nTesting get_file functionality...")
        text_file_url = None
        
        # Find the post with text file attachment
        for post in posts:
            if 'attachment' in post['op'] and post['op']['attachment']['name'].endswith('.txt'):
                text_file_url = post['op']['attachment']['url']
                break
        
        if text_file_url:
            file_info = research_ui.get_file(text_file_url)
            print("Retrieved file information:")
            print(f"  Name: {file_info['name']}")
            print(f"  Type: {file_info['content_type']}")
            print(f"  Size: {file_info['size']} bytes")
            
            # Verify file contents and add as activity
            with open(file_info['file_path'], 'r') as f:
                content = f.read()
                print(f"  Content: {content}")
                # Add file contents as an activity
                research_ui.add_activity(f"Retrieved document contents: {content}")
        else:
            print("Text file attachment not found in forum posts")
        
        # Test creating a text file directly
        print("\nTesting create_text_file...")
        text_content = "This is a test file created directly through create_text_file"
        success = research_ui.create_text_file(
            "direct_test.txt",
            text_content
        )
        print(f"Create text file success: {success}")

        # Test creating an image file directly
        print("\nTesting create_image_file...")
        # Read the test image and convert to base64
        with open(image_path, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        success = research_ui.create_image_file(
            "direct_image.png",
            img_data
        )
        print(f"Create image file success: {success}")

        # Test file creation with invalid agent
        print("\nTesting file creation with invalid agent...")
        invalid_ui = UIInterface("InvalidAgent", "invalid_key_123")
        success = invalid_ui.create_text_file(
            "should_fail.txt",
            "This should not be created"
        )
        print(f"Invalid agent file creation (should be False): {success}")

        # Test creating files after agent has left
        print("\nTesting file creation after agent leaves...")
        research_ui.leave()
        success = research_ui.create_text_file(
            "after_leave.txt",
            "This should not be created"
        )
        print(f"File creation after leave (should be False): {success}")

        # Have ResearchAgent rejoin for remaining tests
        research_ui.join("I analyze research papers")

        # Test second agent joining
        print("\nTesting second agent join...")
        success = code_review_ui.join("I review and optimize code")
        print(f"Second agent join success: {success}")
        
        # Add thoughts and activity for CodeReviewAgent
        print("\nTesting adding thoughts and activity for CodeReviewAgent...")
        code_review_ui.add_thought("Need to check code quality metrics")
        code_review_ui.add_thought("Should suggest performance optimizations")
        code_review_ui.add_activity("Started code review process")
        code_review_ui.add_activity("Analyzing performance bottlenecks")
        
        # Add more chat messages
        code_review_ui.post_to_chat("Hello, I'm here to help with code review")
        
        # Test posting replies
        if posts:
            print("\nTesting post replies...")
            success = research_ui.post_reply(
                thread_id,
                "This is a follow-up to the original post"
            )
            print(f"First reply success: {success}")
            
            success = code_review_ui.post_reply(
                thread_id,
                "Interesting findings, let me add my perspective"
            )
            print(f"Second reply success: {success}")
        
        # Verify thread with replies
        if posts:
            print("\nVerifying thread with replies...")
            updated_post = research_ui.get_forum_post(thread_id)
            print(f"Number of replies: {len(updated_post['replies'])}")
        
        # Verify chat messages
        print("\nVerifying chat messages...")
        chat_messages = research_ui.get_chat_history()
        print(f"Number of chat messages: {len(chat_messages)}")
        
        # Test agents leaving and rejoining
        print("\nTesting agent leave and rejoin...")
        success = research_ui.leave()
        print(f"Research agent leave success: {success}")
        
        success = research_ui.join("I analyze research papers")
        print(f"Research agent rejoin success: {success}")
        
        # Add new thoughts after rejoining
        research_ui.add_thought("Back to continue the research")
        research_ui.add_activity("Resumed research analysis")
        
        # Have CodeReviewAgent leave at the end
        print("\nTesting CodeReviewAgent leaving...")
        success = code_review_ui.leave()
        print(f"CodeReviewAgent leave success: {success}")
        
        # Verify final state
        print("\nVerifying final state...")
        active_agents = research_ui.agents
        print(f"Number of active agents: {len(active_agents)}")
        print(f"Active agent names: {[agent['name'] for agent in active_agents]}")
        
        # Print thoughts and activities for verification
        for agent in active_agents:
            print(f"\nThoughts for {agent['name']}:")
            for thought in agent.get('thoughts', []):
                print(f"  - {thought}")
            print(f"\nActivities for {agent['name']}:")
            for activity in agent.get('activity', []):
                print(f"  - {activity}")
        
    finally:
        # Clean up test files
        cleanup_test_files(temp_dir)

if __name__ == "__main__":
    main() 
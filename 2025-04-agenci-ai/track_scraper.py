import requests
import time
import json
import re
import csv
from bs4 import BeautifulSoup, Tag

def read_track_urls(filename='tracks.txt'):
    """Read track URLs from file."""
    with open(filename, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    return urls

def fetch_track_content(url):
    """Fetch content from a track URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_skills(html_content):
    """Extract skills from 'Skills you will gain' section"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the skills section heading
    skills_heading = soup.find('h2', string=re.compile(r'Skills you will gain', re.IGNORECASE))
    if not skills_heading:
        # Try to find by id or class
        skills_heading = soup.find('h2', {'id': re.compile(r'skillsSection', re.IGNORECASE)}) or \
                        soup.find('h2', {'class': re.compile(r'skillsSection', re.IGNORECASE)})
    
    if skills_heading:
        # Find the next ul element after the heading
        skills_list = skills_heading.find_next('ul')
        if skills_list and isinstance(skills_list, Tag):
            # Extract all li elements and get their text content
            skills = []
            for li in skills_list.find_all('li'):
                if isinstance(li, Tag):
                    skill_text = li.get_text(strip=True)
                    if skill_text:
                        skills.append(skill_text)
            return skills
    
    return []

def extract_detailed_description(html_content):
    """Extract detailed description section and convert to markdown"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the description section heading
    desc_heading = soup.find('h2', string=re.compile(r'Description', re.IGNORECASE))
    if not desc_heading:
        # Try to find by id or class
        desc_heading = soup.find('h2', {'id': re.compile(r'description', re.IGNORECASE)}) or \
                      soup.find('h2', {'class': re.compile(r'description', re.IGNORECASE)})
    
    if desc_heading:
        # Find the content section after the heading
        content_section = desc_heading.find_next('div', class_=re.compile(r'productDescriptionSection__content', re.IGNORECASE))
        if not content_section:
            # Fallback to generic content class
            content_section = desc_heading.find_next('div', class_=re.compile(r'content', re.IGNORECASE))
        
        if content_section:
            # Convert the entire content section to markdown
            markdown_content = convert_html_to_markdown(content_section)
            return markdown_content
    
    return ''

def convert_html_to_markdown(element):
    """Convert HTML element to markdown format"""
    markdown_lines = []
    
    # Process all elements in the content section
    for child in element.find_all(recursive=True):
        if child.name == 'h2':
            text = child.get_text(strip=True)
            if text and f"## {text}" not in markdown_lines:
                markdown_lines.append(f"## {text}")
        elif child.name == 'h3':
            text = child.get_text(strip=True)
            if text and f"### {text}" not in markdown_lines:
                markdown_lines.append(f"### {text}")
        elif child.name == 'p':
            # Skip paragraphs that only contain images or picture elements
            text = child.get_text(strip=True)
            if text and not child.find('picture') and not child.find('img'):
                if text not in markdown_lines:
                    markdown_lines.append(text)
        elif child.name == 'ul' and not child.find_parent('li'):
            # Only process ul that are not nested in li elements
            ul_items = []
            for li in child.find_all('li', recursive=False):
                li_text = li.get_text(strip=True)
                if li_text:
                    # Handle bold text in list items
                    bold_elements = li.find_all(['b', 'strong'])
                    if bold_elements:
                        for bold_elem in bold_elements:
                            bold_text = bold_elem.get_text(strip=True)
                            li_text = li_text.replace(bold_text, f"**{bold_text}**")
                    ul_items.append(f"- {li_text}")
            
            # Add items if they're not already in markdown_lines
            for item in ul_items:
                if item not in markdown_lines:
                    markdown_lines.append(item)
        elif child.name == 'ol' and not child.find_parent('li'):
            # Only process ol that are not nested in li elements
            ol_items = []
            for i, li in enumerate(child.find_all('li', recursive=False), 1):
                li_text = li.get_text(strip=True)
                if li_text:
                    # Handle bold text in list items
                    bold_elements = li.find_all(['b', 'strong'])
                    if bold_elements:
                        for bold_elem in bold_elements:
                            bold_text = bold_elem.get_text(strip=True)
                            li_text = li_text.replace(bold_text, f"**{bold_text}**")
                    ol_items.append(f"{i}. {li_text}")
            
            # Add items if they're not already in markdown_lines
            for item in ol_items:
                if item not in markdown_lines:
                    markdown_lines.append(item)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_lines = []
    for line in markdown_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    return '\n\n'.join(unique_lines)

def extract_track_info(html_content):
    """Extract track information from HTML content."""
    try:
        # Find the JSON-LD script tags (we want the second one)
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = soup.find_all('script', {'type': 'application/ld+json'})
        
        if len(script_tags) < 2:
            return None
        
        script_tag = script_tags[1]  # Get the second script tag
        
        if not script_tag:
            return None
        
        # Parse the JSON data
        json_data = json.loads(script_tag.get_text())
        
        # Extract skills and detailed description from HTML
        skills = extract_skills(html_content)
        detailed_description = extract_detailed_description(html_content)
        
        # Extract required information
        track_name = json_data.get('name', '')
        
        # Determine dialect from title
        dialect = "Standard SQL"
        if "MySQL" in track_name:
            dialect = "MySQL"
        elif "PostgreSQL" in track_name:
            dialect = "PostgreSQL"
        elif "SQL Server" in track_name:
            dialect = "SQL Server"
        
        # Determine purpose from title
        purpose = "practice" if "Practice" in track_name else "learn"
        
        track_info = {
            'name': track_name,
            'description': json_data.get('description', ''),
            'detailed_description': detailed_description,
            'price': json_data.get('offers', {}).get('price', ''),
            'hours': json_data.get('timeRequired', '').replace('PT', '').replace('H', ''),
            'level': json_data.get('educationalLevel', ''),
            'dialect': dialect,
            'purpose': purpose,
            'skills': skills,
            'course_urls': []
        }
        
        # Extract course URLs from hasPart
        if 'hasPart' in json_data:
            for course in json_data['hasPart']:
                if 'url' in course:
                    track_info['course_urls'].append(course['url'])
        
        return track_info
        
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        print(f"Error parsing track info: {e}")
        return None

def save_tracks_to_csv(tracks_data, filename='tracks.csv'):
    """Save tracks data to CSV file with specified columns"""
    fieldnames = ['title', 'url', 'exercises', 'dialect', 'hours', 'kind', 'description', 'detailed_description', 'skills', 'purpose', 'level', 'price']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for track in tracks_data:
            # Convert skills list to comma-separated string
            skills_str = ', '.join(track['skills']) if track['skills'] else ''
            
            row = {
                'title': track['name'],
                'url': track['url'],
                'exercises': '',  # Leave empty as requested
                'dialect': track['dialect'],
                'hours': track['hours'],
                'kind': 'Track',  # Set to 'Track' as requested
                'description': track['description'],
                'detailed_description': track['detailed_description'],
                'skills': skills_str,
                'purpose': track['purpose'],
                'level': track['level'],
                'price': track['price']
            }
            writer.writerow(row)
    
    print(f"\nSaved {len(tracks_data)} tracks to {filename}")

def main():
    # Read URLs from tracks.txt
    urls = read_track_urls()
    print(f"Found {len(urls)} track URLs")
    
    # Fetch content and extract info for each URL
    tracks_data = []
    for i, url in enumerate(urls, 1):
        print(f"Processing {i}/{len(urls)}: {url}")
        content = fetch_track_content(url)
        
        if content:
            track_info = extract_track_info(content)
            if track_info:
                track_info['url'] = url
                tracks_data.append(track_info)
                skills_count = len(track_info['skills'])
                print(f"  ✓ Extracted: {track_info['name']} - ${track_info['price']} - {track_info['hours']}h - {track_info['level']} - {track_info['dialect']} - {track_info['purpose']} - {skills_count} skills")
            else:
                print(f"  ✗ Failed to extract track info")
        else:
            print(f"  ✗ Failed to fetch")
        
        # Small delay to be polite
        time.sleep(0.5)
    
    print(f"\nSuccessfully processed {len(tracks_data)} tracks")
    
    # Print summary
    print("\n" + "="*80)
    print("TRACK SUMMARY")
    print("="*80)
    for track in tracks_data:
        print(f"\nTrack: {track['name']}")
        print(f"Price: ${track['price']}")
        print(f"Duration: {track['hours']} hours")
        print(f"Level: {track['level']}")
        print(f"Dialect: {track['dialect']}")
        print(f"Purpose: {track['purpose']}")
        print(f"Courses: {len(track['course_urls'])}")
        print(f"Skills: {len(track['skills'])}")
        if track['skills']:
            print(f"  Skills list: {', '.join(track['skills'][:3])}{'...' if len(track['skills']) > 3 else ''}")
        print(f"Description: {track['description'][:100]}...")
        if track['detailed_description']:
            print(f"Detailed description: {track['detailed_description'][:100]}...")
    
    # Save tracks data to CSV
    if tracks_data:
        save_tracks_to_csv(tracks_data)
    
    return tracks_data

if __name__ == "__main__":
    main()

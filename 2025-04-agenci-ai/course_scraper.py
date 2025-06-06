import json
import requests
import re
import csv
from bs4 import BeautifulSoup

# Load JSON from file
with open("courses.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract the URLs
urls = [item["url"] for item in data.get("itemListElement", [])]

# Function to extract course data from JSON-LD
def extract_course_data(json_ld_data):
    """Extract specific fields from JSON-LD course data"""
    course_info = {
        'type': json_ld_data.get('@type'),
        'title': json_ld_data.get('name'),
        'description': json_ld_data.get('description'),
        'price': None,
        'currency': None,
        'courseWorkload_hours': None,
        'educationalLevel': json_ld_data.get('educationalLevel'),
        'skills': [],
        'detailed_description': '',
        'exercises_count': None
    }
    
    # Extract price and currency from offers
    offers = json_ld_data.get('offers')
    if offers:
        course_info['price'] = offers.get('price')
        course_info['currency'] = offers.get('priceCurrency')
    
    # Extract course workload and convert to hours
    workload = json_ld_data.get('timeRequired')
    if not workload:
        # Try to get from courseInstance
        course_instances = json_ld_data.get('hasCourseInstance')
        if course_instances and isinstance(course_instances, list) and len(course_instances) > 0:
            workload = course_instances[0].get('courseWorkload')
    
    if workload:
        # Parse ISO 8601 duration format (PT10H -> 10 hours)
        match = re.search(r'PT(\d+)H', workload)
        if match:
            course_info['courseWorkload_hours'] = int(match.group(1))
    
    return course_info

# Function to extract skills from HTML
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
        if skills_list:
            # Extract all li elements and get their text content
            skills = []
            for li in skills_list.find_all('li'):
                skill_text = li.get_text(strip=True)
                if skill_text:
                    skills.append(skill_text)
            return skills
    
    return []

# Function to extract detailed description and convert to markdown
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
        content_section = desc_heading.find_next('div', class_=re.compile(r'content', re.IGNORECASE))
        if not content_section:
            # Try to find productDescriptionSection__content
            content_section = desc_heading.find_next('div', class_=re.compile(r'productDescriptionSection__content', re.IGNORECASE))
        
        if content_section:
            markdown_content = []
            
            # Process all child divs in the content section
            for div in content_section.find_all('div', class_=re.compile(r'course_information', re.IGNORECASE)):
                # Convert div content to markdown
                div_markdown = convert_html_to_markdown(div)
                if div_markdown.strip():
                    markdown_content.append(div_markdown)
            
            return '\n\n'.join(markdown_content)
    
    return ''

# Function to extract exercises count
def extract_exercises_count(html_content):
    """Extract number of exercises/coding challenges"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for productSummarySection items
    summary_items = soup.find_all('span', class_=re.compile(r'productSummarySection__itemLabel', re.IGNORECASE))
    
    for label_span in summary_items:
        label_text = label_span.get_text(strip=True).lower()
        
        # Check if this is the coding challenges/exercises item
        if 'coding challenges' in label_text or 'exercises' in label_text:
            # Find the corresponding value span (next sibling)
            value_span = label_span.find_next_sibling('span', class_=re.compile(r'productSummarySection__itemValue', re.IGNORECASE))
            if value_span:
                try:
                    # Extract and convert to integer
                    exercises_text = value_span.get_text(strip=True)
                    # Remove any non-digit characters and convert to int
                    exercises_count = int(re.sub(r'\D', '', exercises_text))
                    return exercises_count
                except (ValueError, AttributeError):
                    continue
    
    return None

# Function to convert HTML elements to markdown
def convert_html_to_markdown(element):
    """Convert HTML element to markdown format"""
    markdown_lines = []
    
    for child in element.children:
        if child.name == 'h2':
            markdown_lines.append(f"## {child.get_text(strip=True)}")
        elif child.name == 'h3':
            markdown_lines.append(f"### {child.get_text(strip=True)}")
        elif child.name == 'p':
            # Skip paragraphs that only contain images
            text = child.get_text(strip=True)
            if text and not (len(child.find_all('img')) > 0 and not text):
                markdown_lines.append(text)
        elif child.name == 'ul':
            for li in child.find_all('li'):
                li_text = li.get_text(strip=True)
                if li_text:
                    markdown_lines.append(f"- {li_text}")
        elif child.name == 'ol':
            for i, li in enumerate(child.find_all('li'), 1):
                li_text = li.get_text(strip=True)
                if li_text:
                    markdown_lines.append(f"{i}. {li_text}")
        elif hasattr(child, 'get_text'):
            # Handle other text elements
            text = child.get_text(strip=True)
            if text:
                markdown_lines.append(text)
    
    return '\n\n'.join(markdown_lines)

# Function to find and parse JSON-LD scripts
def find_course_json_ld(html_content):
    """Find and parse JSON-LD scripts containing Course data"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all script tags with type="application/ld+json"
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    
    courses = []
    for script in json_ld_scripts:
        try:
            json_data = json.loads(script.string)
            
            # Handle both single objects and arrays
            if isinstance(json_data, list):
                for item in json_data:
                    if item.get('@type') == 'Course':
                        courses.append(extract_course_data(item))
            elif json_data.get('@type') == 'Course':
                courses.append(extract_course_data(json_data))
                
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing JSON-LD: {e}")
            continue
    
    return courses

# Store all extracted courses
all_courses = []

# Fetch HTML for each URL
for url in urls:
    print(f"Fetching: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an error for bad status codes
        html_content = response.text
        
        print(f"Fetched {len(html_content)} characters from {url}")
        
        # Extract course data from JSON-LD
        courses = find_course_json_ld(html_content)
        if courses:
            # Extract skills, detailed description, and exercises count for each course
            skills = extract_skills(html_content)
            detailed_desc = extract_detailed_description(html_content)
            exercises_count = extract_exercises_count(html_content)
            
            for course in courses:
                course['source_url'] = url  # Add source URL for reference
                course['skills'] = skills  # Add skills to course data
                course['detailed_description'] = detailed_desc  # Add detailed description
                course['exercises_count'] = exercises_count  # Add exercises count
                all_courses.append(course)
            
            print(f"Extracted {len(courses)} course(s) from {url}")
            if skills:
                print(f"Found {len(skills)} skills: {skills[:2]}{'...' if len(skills) > 2 else ''}")
            else:
                print("No skills section found")
            
            if detailed_desc:
                print(f"Found detailed description ({len(detailed_desc)} characters)")
            else:
                print("No detailed description found")
            
            if exercises_count is not None:
                print(f"Found {exercises_count} exercises/coding challenges")
            else:
                print("No exercises count found")
        else:
            print(f"No course JSON-LD found in {url}")
        
        print()

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

# Print summary
print(f"\nTotal courses extracted: {len(all_courses)}")
for i, course in enumerate(all_courses, 1):
    skills_count = len(course.get('skills', []))
    exercises_info = f" - {course['exercises_count']} exercises" if course.get('exercises_count') is not None else ""
    print(f"{i}. {course['title']} - {course['price']} {course['currency']} - {course['courseWorkload_hours']}h - {course['educationalLevel']} - {skills_count} skills{exercises_info}")
    print(f"Source: {course['source_url']}")
    print(f"Type: {course['type']}")

    # Display skills as markdown list if available
    if course.get('skills'):
        print("   Skills:")
        for skill in course['skills']:
            print(f"   - {skill}")
    print(f"{course['description']}")
    print(f"{course['detailed_description']}")

# Save extracted courses to CSV file
if all_courses:
    csv_filename = 'courses_extracted.csv'
    
    # Define CSV columns with both description fields
    fieldnames = ['title', 'url', 'exercises', 'dialect', 'hours', 'kind', 'description', 'detailed_description', 'skills', 'purpose', 'level', 'price']
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write course data
        for course in all_courses:
            # Format skills as a single string with newlines
            skills_text = '\n'.join(course.get('skills', [])) if course.get('skills') else ''
            
            # Format price with currency
            price_text = ''
            if course.get('price') and course.get('currency'):
                price_text = f"{course['price']} {course['currency']}"
            elif course.get('price'):
                price_text = str(course['price'])
            
            # Prepare row data according to specified columns
            row_data = {
                'title': course.get('title', ''),
                'url': course.get('source_url', ''),
                'exercises': course.get('exercises_count', ''),
                'dialect': '',  # Leave empty as requested
                'hours': course.get('courseWorkload_hours', ''),
                'kind': 'Course',  # Fill as "Course" as requested
                'description': course.get('description', ''),  # Short description from JSON-LD
                'detailed_description': course.get('detailed_description', ''),  # Full description in markdown
                'skills': skills_text,
                'purpose': '',  # Leave empty as requested
                'level': course.get('educationalLevel', ''),
                'price': price_text
            }
            
            writer.writerow(row_data)
    
    print(f"\nCourses saved to {csv_filename}")
    print(f"CSV contains {len(all_courses)} courses with columns: {', '.join(fieldnames)}")
else:
    print("\nNo courses extracted, CSV file not created.")

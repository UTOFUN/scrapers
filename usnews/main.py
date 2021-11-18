import requests
import lxml.html
import json
import unicodedata

urls = json.load(fp=open("urls.json"))


def _get_usnews_tree(url):
    res = requests.get(
        url,
        headers={
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44"
        },
    )
    return lxml.html.fromstring(res.content)


def _table_elem_to_json(table_elem):
    return {
        key: value
        for (key, value) in [
            (
                node.xpath("*")[0].text_content(),
                node.xpath("*")[1].attrib["href"]
                if node.xpath("*")[1].tag == "a"
                else node.xpath("*")[1].text_content(),
            )
            for node in table_elem
        ]
    }


def _get_general_data(tree):
    general_table = tree.xpath("//div[@class='optly-school-information-section']/div[1]/div[1]")[0]
    return _table_elem_to_json(general_table)


def _get_ranking_data(tree):
    ranking = tree.xpath("//ul[contains(@class, 'RankList')]/li")
    return [
        {
            "position": node[0].text_content().split("#")[1],
            "ranking": unicodedata.normalize("NFKD", node[1].text_content()).split(" (")[0],  # remove (tie)
        }
        for node in [[el for el in els.xpath("a/*") if el.tag != "span"] for els in ranking]
    ]


def _get_admission_data(tree):
    admission_table = tree.xpath("//section[@id='admissions']/div[2]")[0]
    return _table_elem_to_json(admission_table)


def _get_academic_life_data(tree):
    academic_life_table = tree.xpath("//section[@id='academic-life']/div[2]/div")
    return _table_elem_to_json(academic_life_table)


# undergrade enrollment is not on the overview page
def _get_student_life_data(student_life_tree):
    student_life_table = student_life_tree.xpath("//h2[@id='StudentBody']/following-sibling::div")[0]
    return _table_elem_to_json(student_life_table)


def _get_tuition_data(tree):
    tuition_table = tree.xpath("//section[@id='tuition']/div[2]/div")[1:]
    return _table_elem_to_json(tuition_table)


def get_school_info(url):
    tree = _get_usnews_tree(url)
    general = _get_general_data(tree)
    ranking = _get_ranking_data(tree)
    admission = _get_admission_data(tree)
    academic_life = _get_academic_life_data(tree)
    student_life = _get_student_life_data(_get_usnews_tree(f"{url}/student-life"))
    tuition = _get_tuition_data(tree)

    return {
        "school_type": general["School Type"].split(", Coed")[0],
        "is_religious": general["Religious Affiliation"] != "None",
        "website": general["School Website"],
        "phone": "".join([n for n in general["Phone"] if n.isdigit()]),
        "ranking": {
            "ranking": ranking[0]["ranking"],
            "position": ranking[0]["position"],
        },
        "acceptance_rate": admission[[key for key in admission.keys() if "acceptance" in key][0]].split("%")[0],
        "graduation_rate": academic_life["4-year graduation rate"].split("%")[0],
        "undergrad_pop": student_life["Total undergraduate enrollment"].split("(")[0].replace(",", ""),
        "faculty_ratio": {
            "student": academic_life["Student-faculty ratio"].split(":")[0],
            "faculty": academic_life["Student-faculty ratio"].split(":")[1],
        },
        "male_percentage": student_life["Degree-seeking student gender distribution"].split(" men")[1].split("%")[0],
        "estimated_tution": tuition["Tuition and fees"].split("(")[0].replace(",", "").replace("$", ""),
        "cost_of_living": tuition["Room and board"].split("(")[0].replace(",", "").replace("$", ""),
    }


print(get_school_info("https://www.usnews.com/best-colleges/nyu-2785"))

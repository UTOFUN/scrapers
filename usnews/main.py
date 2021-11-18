import requests
import lxml.html
import unicodedata
from typing import Optional
from pydantic import BaseModel


class Ranking(BaseModel):
    list: str
    position: Optional[int] = None


class FacultyRatio(BaseModel):
    student: int
    faculty: int


class School(BaseModel):
    school_type: str
    is_religious: bool
    website: str
    phone: str
    rankings: list[Ranking]
    acceptance_rate: int
    graduation_rate: Optional[int]
    undergrad_pop: int
    faculty_ratio: FacultyRatio
    male_percentage: int
    cost_of_living: int
    estimated_tution: Optional[int] = None
    estimated_tution_in_state: Optional[int] = None
    estimated_tution_out_of_state: Optional[int] = None


def _get_usnews_tree(url):
    res = requests.get(
        url,
        headers={
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44"
        },
    )
    return lxml.html.fromstring(res.content)


def _table_elem_to_json(table_elem):
    """contert table element on page to json"""
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


def get_general(tree):
    """get general data from usnews page"""
    general = _get_general_data(tree)
    return {
        "school_type": general["School Type"].split(", Coed")[0],
        "is_religious": general["Religious Affiliation"] != "None",
        "website": general["School Website"],
        "phone": "".join([n for n in general["Phone"] if n.isnumeric()]),
    }


def _get_ranking_data(tree):
    rankings = tree.xpath("//ul[contains(@class, 'RankList')]/li")
    return [
        {
            "position": node[0].text_content().replace("#", ""),
            "list": unicodedata.normalize("NFKD", node[1].text_content()).split(" (")[0],  # remove (tie)
        }
        for node in [[el for el in els.xpath("a/*") if el.tag != "span"] for els in rankings]
    ]


def get_ranking(tree):
    rankings = _get_ranking_data(tree)
    return (
        {
            "rankings": [
                Ranking(
                    **{
                        "list": ranking["list"],
                        "position": int(ranking["position"]) if ranking["position"].isnumeric() else None,
                    }
                )
                for ranking in rankings
            ]
        }
        if rankings
        else None
    )


def _get_admission_data(tree):
    admission_table = tree.xpath("//section[@id='admissions']/div[2]")[0]
    return _table_elem_to_json(admission_table)


def get_admission(tree):
    admission = _get_admission_data(tree)
    return {
        "acceptance_rate": int(admission[[key for key in admission.keys() if "acceptance" in key][0]].split("%")[0])
    }


def _get_academic_life_data(tree):
    academic_life_table = tree.xpath("//section[@id='academic-life']/div[2]/div")
    return _table_elem_to_json(academic_life_table)


def get_academic_life(tree):
    academic_life = _get_academic_life_data(tree)
    return {
        "graduation_rate": int(academic_life["4-year graduation rate"].split("%")[0])
        if academic_life["4-year graduation rate"].split("%")[0].isnumeric()
        else None,
        "faculty_ratio": {
            "student": int(academic_life["Student-faculty ratio"].split(":")[0]),
            "faculty": int(academic_life["Student-faculty ratio"].split(":")[1]),
        },
    }


# undergrade enrollment is not on the overview page
def _get_student_life_data(student_life_tree):
    student_life_table = student_life_tree.xpath("//h2[@id='StudentBody']/following-sibling::div")[0]
    return _table_elem_to_json(student_life_table)


def get_student_life(student_life_tree):
    student_life = _get_student_life_data(student_life_tree)
    return {
        "undergrad_pop": int(student_life["Total undergraduate enrollment"].split("(")[0].replace(",", "")),
        "male_percentage": student_life["Degree-seeking student gender distribution"].split(" men")[1].split("%")[0],
    }


def _get_tuition_data(tree):
    tuition_table = tree.xpath("//section[@id='tuition']/div[2]/div")[1:]
    return _table_elem_to_json(tuition_table)


def get_tuition(tree):
    tuition = _get_tuition_data(tree)
    if "Tuition and fees" in tuition.keys():
        return {
            "estimated_tution": tuition["Tuition and fees"].split("(")[0].replace(",", "").replace("$", ""),
            "cost_of_living": tuition["Room and board"].split("(")[0].replace(",", "").replace("$", ""),
        }
    else:
        return {
            "estimated_tution_in_state": tuition["In-state tuition and fees"]
            .split("(")[0]
            .replace(",", "")
            .replace("$", ""),
            "estimated_tution_out_of_state": tuition["Out-of-state tuition and fees"]
            .split("(")[0]
            .replace(",", "")
            .replace("$", ""),
            "cost_of_living": tuition["Room and board"].split("(")[0].replace(",", "").replace("$", ""),
        }


def get_school_info(url):
    tree = _get_usnews_tree(url)
    student_life_tree = _get_usnews_tree(f"{url}/student-life")

    return School(
        **{
            **get_general(tree),
            **get_ranking(tree),
            **get_admission(tree),
            **get_academic_life(tree),
            **get_student_life(student_life_tree),
            **get_tuition(tree),
        }
    )


if __name__ == "__main__":
    print(get_school_info("https://www.usnews.com/best-colleges/fashion-institute-of-technology-2866"))

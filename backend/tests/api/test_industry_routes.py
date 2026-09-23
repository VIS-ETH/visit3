from httpx import AsyncClient

INDUSTRIES = "/api/industries"


async def test_staff_creates_and_lists_industries(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
):
    created = await client.post(
        INDUSTRIES, json={"name": "  Software  "}, headers=staff_headers
    )
    listed = await client.get(INDUSTRIES, headers=company_headers)

    assert created.status_code == 200
    assert created.json()["name"] == "Software"
    assert [entry["name"] for entry in listed.json()] == ["Software"]


async def test_industries_are_sorted_by_name(
    client: AsyncClient, staff_headers: dict[str, str]
):
    for name in ["Pharma", "Banking", "Software"]:
        await client.post(INDUSTRIES, json={"name": name}, headers=staff_headers)

    response = await client.get(INDUSTRIES, headers=staff_headers)

    assert [entry["name"] for entry in response.json()] == [
        "Banking",
        "Pharma",
        "Software",
    ]


async def test_duplicate_industry_name_is_refused(
    client: AsyncClient, staff_headers: dict[str, str]
):
    await client.post(INDUSTRIES, json={"name": "Software"}, headers=staff_headers)

    response = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.industry_name_exists"


async def test_industry_is_renamed(client: AsyncClient, staff_headers: dict[str, str]):
    created = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )

    response = await client.patch(
        f"{INDUSTRIES}/{created.json()['id']}",
        json={"name": "Software engineering"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Software engineering"


async def test_renaming_to_a_taken_name_is_refused(
    client: AsyncClient, staff_headers: dict[str, str]
):
    await client.post(INDUSTRIES, json={"name": "Banking"}, headers=staff_headers)
    created = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )

    response = await client.patch(
        f"{INDUSTRIES}/{created.json()['id']}",
        json={"name": "Banking"},
        headers=staff_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "error.industry_name_exists"


async def test_deleted_industry_frees_its_name_and_leaves_the_list(
    client: AsyncClient, staff_headers: dict[str, str]
):
    created = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )

    deleted = await client.delete(
        f"{INDUSTRIES}/{created.json()['id']}", headers=staff_headers
    )
    recreated = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )
    listed = await client.get(INDUSTRIES, headers=staff_headers)

    assert deleted.status_code == 200
    assert recreated.status_code == 200
    assert [entry["id"] for entry in listed.json()] == [recreated.json()["id"]]


async def test_unknown_industry_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.delete(
        f"{INDUSTRIES}/3fa85f64-5717-4562-b3fc-2c963f66afa6", headers=staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.industry_not_found"


async def test_deleting_an_industry_removes_it_from_company_profiles(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
    complete_company_profile,
):
    created = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=staff_headers
    )
    await complete_company_profile(company_headers, industry_ids=[created.json()["id"]])

    await client.delete(f"{INDUSTRIES}/{created.json()['id']}", headers=staff_headers)
    profile = await client.get("/api/company/me/profile", headers=company_headers)

    assert profile.json()["industries"] == []


async def test_company_user_cannot_manage_the_catalogue(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.post(
        INDUSTRIES, json={"name": "Software"}, headers=company_headers
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"

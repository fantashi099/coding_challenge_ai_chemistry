from .models import VideoPlan


_PLANS = {
    "how does the ph scale work?": {
        "title": "How the pH Scale Works",
        "scenes": [
            {
                "heading": "pH measures acidity",
                "visual_text": "A compact scale for hydrogen ion concentration",
                "narration": "The pH scale tells us how acidic or basic a water-based solution is. It tracks hydrogen ions, written H plus. More available hydrogen ions means a more acidic solution and a lower pH value.",
                "visual_kind": "title",
            },
            {
                "heading": "Reading the scale",
                "visual_text": "0–6 acidic\n7 neutral\n8–14 basic",
                "narration": "The familiar scale runs from zero to fourteen. Seven is neutral, like pure water near room temperature. Values below seven are acidic. Values above seven are basic, sometimes called alkaline.",
                "visual_kind": "ph_scale",
            },
            {
                "heading": "Every step is tenfold",
                "visual_text": "pH 3 has 10× more H⁺ than pH 4",
                "narration": "pH is logarithmic, so neighboring numbers are not equal-sized steps. A solution at pH three has ten times the hydrogen ion concentration of pH four, and one hundred times that of pH five.",
                "visual_kind": "bullets",
            },
            {
                "heading": "Everyday examples",
                "visual_text": "Lemon ≈ 2\nWater ≈ 7\nSoap ≈ 10",
                "narration": "Lemon juice is around pH two, water is near seven, and soapy water may be around ten. Exact values vary with concentration and temperature, but their positions reveal useful chemical behavior.",
                "visual_kind": "ph_scale",
            },
            {
                "heading": "The key idea",
                "visual_text": "Lower pH → more H⁺\nHigher pH → less H⁺\nEach step → factor of 10",
                "narration": "Remember three points: lower pH means more hydrogen ions, seven is neutral under standard classroom conditions, and every one-unit change represents a factor of ten. That is why small pH changes can matter greatly.",
                "visual_kind": "recap",
            },
        ],
    },
    "why do atoms form covalent bonds?": {
        "title": "Why Atoms Form Covalent Bonds",
        "scenes": [
            {
                "heading": "Atoms seek lower energy",
                "visual_text": "Bonding can make a more stable arrangement",
                "narration": "Atoms form bonds when the combined arrangement has lower energy than the separated atoms. For many nonmetals, sharing electrons lets each nucleus attract the same electrons and creates a stable covalent bond.",
                "visual_kind": "title",
            },
            {
                "heading": "Valence electrons matter",
                "visual_text": "Outer electrons control most bonding",
                "narration": "The electrons in an atom's outer shell are called valence electrons. These are the electrons most available for bonding. Filled outer shells are especially stable, so atoms often bond to approach that arrangement.",
                "visual_kind": "bullets",
            },
            {
                "heading": "A shared pair",
                "visual_text": "H ·  +  · H  →  H : H",
                "narration": "Consider two hydrogen atoms. Each contributes one electron to a shared pair. Both nuclei attract that pair, so each hydrogen effectively gains access to two electrons, filling its first shell.",
                "visual_kind": "covalent_sharing",
            },
            {
                "heading": "More pairs, stronger links",
                "visual_text": "Single: 1 pair\nDouble: 2 pairs\nTriple: 3 pairs",
                "narration": "Atoms can share one, two, or three electron pairs, producing single, double, or triple bonds. The best arrangement depends on the atoms and geometry, not simply on completing an octet rule.",
                "visual_kind": "covalent_sharing",
            },
            {
                "heading": "The key idea",
                "visual_text": "Shared electrons attract both nuclei\nThe molecule reaches lower energy",
                "narration": "Covalent bonding is therefore not atoms consciously seeking shells. It is an electrostatic, lower-energy arrangement in which shared electrons hold nuclei together. The shell model is a useful prediction tool, while energy explains why bonding occurs.",
                "visual_kind": "recap",
            },
        ],
    },
    "what is the difference between ionic and covalent bonding?": {
        "title": "Ionic vs Covalent Bonding",
        "scenes": [
            {
                "heading": "Two ways atoms bond",
                "visual_text": "Ionic: attraction between ions\nCovalent: shared electrons",
                "narration": "Ionic and covalent bonds both arise from electrical attractions, but they organize electrons differently. Ionic bonding involves oppositely charged ions. Covalent bonding involves atoms held together by shared electron pairs.",
                "visual_kind": "title",
            },
            {
                "heading": "Ionic bonding",
                "visual_text": "Na gives an electron to Cl\nNa⁺ attracts Cl⁻",
                "narration": "In a simplified ionic picture, sodium transfers an electron to chlorine. Sodium becomes positively charged and chlorine becomes negatively charged. Their opposite charges attract throughout a repeating crystal lattice, as in table salt.",
                "visual_kind": "ionic_transfer",
            },
            {
                "heading": "Covalent bonding",
                "visual_text": "Two nonmetals share electron density",
                "narration": "In a covalent bond, atoms share electron density. In a hydrogen molecule, one shared pair is attracted to both nuclei. Covalent bonds commonly join nonmetal atoms into distinct molecules or network structures.",
                "visual_kind": "covalent_sharing",
            },
            {
                "heading": "Typical properties",
                "visual_text": "Ionic: lattices, brittle, conduct when mobile\nCovalent: molecules or networks, varied properties",
                "narration": "Ionic compounds are often crystalline, brittle, and high-melting. They conduct electricity when melted or dissolved because ions can move. Molecular covalent substances often melt lower and usually do not conduct, though exceptions matter.",
                "visual_kind": "bond_comparison",
            },
            {
                "heading": "Compare the models",
                "visual_text": "Ionic → charged particles attract\nCovalent → electron pairs are shared",
                "narration": "Use the models as a continuum, not two perfect boxes. Many bonds have both ionic and covalent character. The practical distinction is whether we describe a lattice of ions or atoms sharing electron density.",
                "visual_kind": "recap",
            },
        ],
    },
}

CURATED_PLANS = {question: VideoPlan.model_validate(plan) for question, plan in _PLANS.items()}


def curated_plan(question: str) -> VideoPlan | None:
    return CURATED_PLANS.get(" ".join(question.casefold().split()))

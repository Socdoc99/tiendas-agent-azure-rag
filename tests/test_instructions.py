import unittest

from app.agent.instructions import AGENT_INSTRUCTIONS


class InstructionTests(unittest.TestCase):
    def test_instructions_restrict_scope_to_store_and_skip_database_for_off_topic(self) -> None:
        self.assertIn(
            "Tu alcance es exclusivamente la operaci\u00f3n y los datos disponibles de la tienda:",
            AGENT_INSTRUCTIONS,
        )
        self.assertIn(
            "no respondas el contenido de esa pregunta y no llames query_database.",
            AGENT_INSTRUCTIONS,
        )
        self.assertIn("Puedo ayudarte con tus ventas, productos,", AGENT_INSTRUCTIONS)

    def test_instructions_forbid_unsupported_exports_and_files(self) -> None:
        self.assertIn("exportar archivos", AGENT_INSTRUCTIONS)
        self.assertIn("generar archivos descargables", AGENT_INSTRUCTIONS)
        self.assertIn("crear Excel", AGENT_INSTRUCTIONS)
        self.assertIn("crear CSV", AGENT_INSTRUCTIONS)
        self.assertIn("crear PDF", AGENT_INSTRUCTIONS)
        self.assertIn("Nunca ofrezcas espont\u00e1neamente esas capacidades.", AGENT_INSTRUCTIONS)
        self.assertIn("te dejo los datos en una tabla lista para copiar.", AGENT_INSTRUCTIONS)
        self.assertIn("No ofrezcas CSV, Excel, PDF ni formatos alternativos.", AGENT_INSTRUCTIONS)

    def test_instructions_require_markdown_tables_for_comparable_rows(self) -> None:
        self.assertIn(
            "Cuando el resultado tenga varias filas comparables, responde usando una tabla",
            AGENT_INSTRUCTIONS,
        )
        self.assertIn("Usa tablas especialmente para:", AGENT_INSTRUCTIONS)
        self.assertIn("resultados con 3 o m\u00e1s filas comparables.", AGENT_INSTRUCTIONS)
        self.assertIn("No pongas tablas dentro de bloques de c\u00f3digo.", AGENT_INSTRUCTIONS)
        self.assertIn(
            "No uses tabla cuando la respuesta sea una \u00fanica cifra o una respuesta simple.",
            AGENT_INSTRUCTIONS,
        )

    def test_instructions_avoid_unnecessary_follow_up_questions(self) -> None:
        self.assertIn("No agregues autom\u00e1ticamente preguntas como:", AGENT_INSTRUCTIONS)
        self.assertIn(
            "Haz una pregunta \u00fanicamente cuando necesites informaci\u00f3n indispensable para",
            AGENT_INSTRUCTIONS,
        )
        self.assertIn(
            "No hagas preguntas finales solo para mantener la conversaci\u00f3n activa.",
            AGENT_INSTRUCTIONS,
        )

"""Registro das fontes disponíveis. Para adicionar uma nova, crie um módulo
com NAME e collect(session, query) e registre aqui."""
from jobtracker.sources import fakejobs, remotive

SOURCES = {
    fakejobs.NAME: fakejobs.collect,
    remotive.NAME: remotive.collect,
}

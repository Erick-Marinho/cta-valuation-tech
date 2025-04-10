"""add size_kb, chunks_count, processed to documentos_originais

Revision ID: b391ae018941
Revises: 2aa3aa042983
Create Date: 2025-04-10 16:05:59.532712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b391ae018941'
down_revision: Union[str, None] = '2aa3aa042983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands manually written ###
    print("Aplicando upgrade: Adicionando colunas size_kb, chunks_count, processed a documentos_originais")
    op.add_column('documentos_originais', sa.Column('size_kb', sa.Float(), nullable=True))
    op.add_column('documentos_originais', sa.Column('chunks_count', sa.Integer(), nullable=True))
    op.add_column('documentos_originais', sa.Column('processed', sa.Boolean(), nullable=True))
    # Nota: Não estamos definindo server_default aqui, pois o modelo SQLModel já define um default=...
    # Se quisesse garantir um valor não nulo para linhas existentes (caso houvesse):
    # op.execute("UPDATE documentos_originais SET size_kb = 0.0 WHERE size_kb IS NULL")
    # op.execute("UPDATE documentos_originais SET chunks_count = 0 WHERE chunks_count IS NULL")
    # op.execute("UPDATE documentos_originais SET processed = false WHERE processed IS NULL")
    print("Colunas adicionadas.")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands manually written ###
    print("Aplicando downgrade: Removendo colunas size_kb, chunks_count, processed de documentos_originais")
    op.drop_column('documentos_originais', 'processed')
    op.drop_column('documentos_originais', 'chunks_count')
    op.drop_column('documentos_originais', 'size_kb')
    print("Colunas removidas.")
    # ### end Alembic commands ###

from plotnine import *
from geopandas import *
import warnings
import getpass
from datetime import datetime
import re
from numpy import arange
import matplotlib.pyplot as plt
from PIL import Image
from shapely.ops import polygonize
import pandas as pd
import io
import os


warnings.filterwarnings('ignore')


def __organization_df__(path):
    # CARREGAR EXCEL E REMOVER ABA GERAL
    df_dict = pd.read_excel(path, sheet_name=None, index_col=None, )
    df_dict.pop('GERAL', None)
    # SEPARA DATAFRAMES CONFORME A CHAVE PROFUNDIDADE
    df_list = []
    for key in df_dict:
        df_temp = df_dict[key]
        df_list.append(df_temp)

    # REMOVER NUMERO DO CABEÇALHO
    for df in range(len(df_list)):
        df_list[df].columns = df_list[df].columns.str.replace(r'\d+', '')

    # CONCATENAR DATAFRAMES E REALIZAR ROUND
    df = pd.concat(df_list)
    df = df.applymap(
        lambda x: round(x, 2) if isinstance(x, (float, int)) else x)  # objeto criado para trabalhar entre dataframe

    return df


def __organization_df_to_shp__(path):
    # CARREGAR EXCEL E REMOVER ABA GERAL
    df_dict = pd.read_excel(path, sheet_name=None, index_col=None)
    df_dict.pop('GERAL', None)
    # SEPARA DATAFRAMES CONFORME A CHAVE PROFUNDIDADE
    df_list = []
    for key in df_dict:
        df_temp = df_dict[key]
        df_list.append(df_temp)

    # REMOVER NUMERO DO CABEÇALHO
    for df in range(len(df_list)):
        df_list[df].columns = df_list[df].columns.str.replace(r'\d+', '')

    # CONCATENAR DATAFRAMES E REALIZAR ROUND
    df_join_pt = pd.concat(df_list)
    df_join_pt = df_join_pt.applymap(
        lambda x: round(x, 2) if isinstance(x, (float, int)) else x)  # objeto criado para trabalhar entre dataframe
    df_join_pt.rename(columns={'id': 'ID'}, inplace=True)

    return df_join_pt


def __creater_dict__(path):
    df = __organization_df__(path)
    dfs = {}
    for prof, df_prof in df.groupby('prof'):
        dfs[prof] = df_prof
    return dfs


def __organization_point__(path, path_pt_shp):
    df = __organization_df__(path)
    pt = geopandas.read_file(path_pt_shp)
    pt.crs = "EPSG:4326"
    pt_df = pt.set_geometry('geometry')
    pt_df.rename(columns={'ID': 'id'}, inplace=True)
    join_df = pd.merge(pt_df, df, how="inner", on=["id"])  # JUNTAR AMOSTRAS DO LAUDOS COM OS O SHP DE PONTOS
    return join_df


def __statistical_module__(path):  # FUNÇÃO PARA CHAMAR TODAS AS FUNNEST
    dfs = __creater_dict__(path)

    # def find_outliers_IQR(df):
    #     q1 = df.quantile(0.25)
    #     q3 = df.quantile(0.75)
    #     IQR = q3 - q1
    #     outliers = df[((df < (q1 - 1.5 * IQR)) | (df > (q3 + 1.5 * IQR)))]
    #     return outliers

    def __statistic__(dfs, prof, determinacoes):
        prof_value = prof
        determinacao_value = determinacoes
        min_value = dfs[prof][determinacoes].min()
        mean_value = round(dfs[prof][determinacoes].mean(), 2)
        max_value = dfs[prof][determinacoes].max()
        std = dfs[prof][determinacoes].std()
        cv_value = round((std / mean_value) * 100, 2)

        statistic_list = {'Determinação': determinacao_value, 'Prof': prof_value, 'Mín': min_value, 'Mean': mean_value,
                          'Máx': max_value, 'CV%': cv_value}

        return statistic_list

    """
        LOOP SOBRE DICIONARIO E APLICANDO A FUNÇÃO '__statistic__'
        RESULTADO: LISTA COM A ESTATISTICA DE CADA DETERMINAÇÃO POR PROFUNDIDADE
    """

    prof = []
    determinacoes = ['zn', 'mn', 'fe', 'cu', 'b', 's', 'sat_al',
                     'al', 'p_meh', 'p_rem', 'p_res', 'sat_k', 'k', 'rel_ca_mg',
                     'sat_mg', 'mg', 'sat_ca', 'ca', 'v', 'ph', 'ctc', 'mo', 'argila']
    for key in dfs:
        prof.append(key)

    statistic_list = []
    for p in prof:
        for value in determinacoes:
            stat = (__statistic__(dfs, p, value))
            statistic_list.append(stat)

    statistic_df = pd.DataFrame(data=statistic_list)

    tolerancia_dict = {'Determinação': ['ctc', 'ph', 'v', 'ca', 'sat_ca', 'mg', 'sat_mg',
                                        'rel_ca_mg', 'k', 'sat_k', 'p_res', 'p_rem', 'p_meh',
                                        'al', 'sat_al', 's', 'b', 'cu', 'fe', 'mn', 'zn'],
                       'tolerancia': [65.0,
                                      7.0,
                                      100.0,
                                      15.0,
                                      100.0,
                                      15.0,
                                      100.0,
                                      50.0,
                                      5.0,
                                      50.0,
                                      120.0,
                                      120.0,
                                      120.0,
                                      3.0,
                                      50.0,
                                      50.0,
                                      3.0,
                                      3.0,
                                      500.0,
                                      80.0,
                                      10.0]}

    tolerancia_df = pd.DataFrame(data=tolerancia_dict)
    results = pd.merge(statistic_df, tolerancia_df, on="Determinação", how='left')

    return results

"""
        BLOCO: GRÁFICO
"""

def __graphic_quantification__(path):
    df = __organization_df__(path)

    """
        ENTRADA -> DF CONCATENADO
        ARESENTAÇÃO GRÁFICA AMOSTRAS/PROFUNIDADE
        RESULTADO: LISTA COM A ESTATISTICA DE CADA DETERMINAÇÃO POR PROFUNDIDADE
    """
    qtd_amostras_perfil = df['prof'].value_counts().reset_index()
    qtd_amostras_perfil.columns = ['Profundidade', 'Nº de amostras']
    qtd_amostras_perfil.loc[len(df.index)] = ['TOTAL', len(df)]
    qtd_amostras_perfil['Relação'] = 'Laudo'

    return qtd_amostras_perfil


def __graphic_quantification_join_(path, path_pt_shp):
    join_df = __organization_point__(path, path_pt_shp)
    """
        ARESENTAÇÃO GRÁFICA JOIN

    """
    qtd_amostras_perfil = join_df['prof'].value_counts().reset_index()
    qtd_amostras_perfil.columns = ['Profundidade', 'Nº de amostras']
    qtd_amostras_perfil.loc[len(join_df.index)] = ['TOTAL', len(join_df)]
    qtd_amostras_perfil['Relação'] = 'Join'

    return qtd_amostras_perfil

def __graphic_quantification_join_e_amostras_1(path, path_pt_shp):
    """
        ARESENTAÇÃO GRÁFICA JOIN/AMOSTRAS

    """
    qtd_join = __graphic_quantification_join_(path, path_pt_shp)
    qtd_df = __graphic_quantification__(path)

    frames = [qtd_df, qtd_join]
    relation_join_df = pd.concat(frames)

    chart = ggplot(data=relation_join_df, mapping=aes(x="Profundidade", y="Nº de amostras", fill='Relação'))
    bars = geom_bar(stat='identity', position='dodge')
    labels = labs(x="Profundidade", y="Nº de amostras", title="Relação Quantidade de Amostras x Pontos")
    theme_grammer = theme(figure_size=(11, 5.5))
    text = geom_text(mapping=aes(label="Nº de amostras"), va="bottom", position=position_dodge(width=1))

    rel_join_plot = chart + bars + labels + theme_grammer + text + theme_minimal() + theme(
        text=element_text(family='DejaVu Sans',
                          size=10),
        axis_title=element_text(face='bold'),
        axis_text=element_text(face='italic'),
        plot_title=element_text(face='bold',
                                size=12))
    return rel_join_plot

def __graphic_quantification_join_e_amostras_df(path, path_pt_shp):
    qtd_join = __graphic_quantification_join_(path, path_pt_shp)
    qtd_df = __graphic_quantification__(path)

    frames = [qtd_df, qtd_join]
    relation_join_df = pd.concat(frames)
    relation_join_df = relation_join_df.sort_values(by='Profundidade')

    return relation_join_df

def __graphic_quantification_join_e_amostras_fig(path, path_pt_shp):
    qtd_join = __graphic_quantification_join_(path, path_pt_shp)
    qtd_df = __graphic_quantification__(path)

    frames = [qtd_df, qtd_join]
    relation_join_df = pd.concat(frames)
    relation_join_df = relation_join_df.sort_values(by='Profundidade')

    fig, ax = plt.subplots(figsize=(12, 8))
    x = arange(len(relation_join_df.Profundidade.unique()))
    bar_width = 0.2

    b1 = ax.bar(x, relation_join_df.loc[relation_join_df['Relação'] == 'Laudo', 'Nº de amostras'],
                width=bar_width)
    b2 = ax.bar(x + bar_width, relation_join_df.loc[relation_join_df['Relação'] == 'Join', 'Nº de amostras'],
                width=bar_width)

    # Fix the x-axes.
    ax.set_xticks(x + bar_width / 2)
    ax.set_xticklabels(relation_join_df.Profundidade.unique())
    ax.legend(relation_join_df.Relação.unique())
    # Add legend.

    # Axis styling.
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#DDDDDD')
    ax.tick_params(bottom=False, left=False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color='#EEEEEE')
    ax.xaxis.grid(False)

    # Add axis and chart labels.
    ax.set_xlabel('Profundidade', labelpad=20)
    ax.set_ylabel('Nº de Amostras', labelpad=15)
    ax.set_title('Relação Nº de amostras x Join', pad=15)

    for bar in ax.patches:
        # The text annotation for each bar should be its height.
        bar_value = bar.get_height()
        # Format the text with commas to separate thousands. You can do
        # any type of formatting here though.
        text = f'{bar_value:,}'
        # This will give the middle of each bar on the x-axis.
        text_x = bar.get_x() + bar.get_width() / 2
        # get_y() is where the bar starts so we add the height to it.
        text_y = bar.get_y() + bar_value
        # If we want the text to be the same color as the bar, we can
        # get the color like so:
        bar_color = bar.get_facecolor()
        # If you want a consistent color, you can just set it as a constant, e.g. #222222
        ax.text(text_x, text_y, text, ha='center', va='bottom', color=bar_color,
                size=12)

        ax.figure.savefig('download/graph_join.png', bbox_inches='tight')

    return ax

"""
BLOCO: VERIFICAÇÃO CONTORNO
"""

def __polygon__(path_co):
    import geopandas
    co = geopandas.read_file(path_co)
    co.crs = "EPSG:4326"
    return co

def __point__(path_pt_shp):
    import geopandas
    pt = geopandas.read_file(path_pt_shp)
    pt.crs = "EPSG:4326"
    return pt

header_error = ''

def __IDENTIFY_CONTOUR_ERROR__(path_co):
    """
    Extrai texto da primeira e ultima pagina, nas quais apresentam informacoes sobre o laboratorio
    entrada -> shp contorno : requer um arquivo shp
    :return: resposta se o cabeçalho esta correto ou não
    """
    USUARIO = getpass.getuser()
    DATA_HORA = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    states = geopandas.read_file(path_co)
    states.crs = "EPSG:4326"
    header_co = states.head()
    name_columns = header_co.columns
    global header_error
    if 'ID' in header_co.columns and 'TALHAO' in header_co.columns and 'CLIENTE' in header_co.columns and 'FAZENDA' in header_co.columns and 'BLOCO' in header_co.columns and 'HECTARES' in header_co.columns and 'GRID' in header_co.columns and 'EMPRESA' in header_co.columns:

        header_error = 'O ARQUIVO POSSUÍ CABEÇALHO DE ACORDO COM OS PARÂMETROS ESTABELECIDOS: ID, TALHAO, CLIENTE, FAZENDA, BLOCO, ACRES, HECTARES e GRID.'

    else:
        header_error = '!#ERROR#!:O ARQUIVO **NÃO** POSSUÍ CABEÇALHO DE ACORDO COM OS PARÂMETROS ESTABELECIDOS : ID, TALHAO, CLIENTE, FAZENDA, BLOCO, ACRES,HECTARES, GRID e EMPRESA. POR FAVOR, USUÁRIO: ' + USUARIO + ' ,CORRIGIR.'
    return header_error

co_overlap = ''

def __count_overlap__(path_co):
    gdf = geopandas.read_file(path_co)  # CALL CO
    gdf.crs = "EPSG:4326"

    """
    IDENTIFICAR SOBREPOSIÇÕES
    entrada -> shp contorno : requer um arquivo shp
    :return: resposta se há sobreposições
    """

    USUARIO = getpass.getuser()
    DATA_HORA = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # create polygon array
    exterior_geom = list(polygonize(gdf.exterior.unary_union))

    # create gdf out of the dissolved features
    gdf_exterior = gpd.GeoDataFrame({'id': range(0, len(exterior_geom))}, geometry=exterior_geom,
                                    crs=gdf.crs).explode().reset_index(drop=True)
    gdf_exterior['id'] = gdf_exterior.index

    # count the intersection of the polygonised unary_union, and the initial gdf
    # the problem with intersection is that it counts if it touches
    gdf_exterior['intersection'] = [len(gdf[gdf.geometry.intersects(feature)]) for feature in gdf_exterior['geometry']]
    gdf_exterior['touching'] = [len(gdf[gdf.geometry.touches(feature)]) for feature in gdf_exterior['geometry']]

    # so the real count must substract polygons that touches. it's cumbersome but, oh well.
    gdf_exterior['count'] = gdf_exterior['intersection'] - gdf_exterior['touching']

    global co_overlap
    if gdf_exterior['intersection'].sum() > len(gdf_exterior.index) or gdf_exterior['touching'].sum() > 1:

        co_overlap = '!#ERROR#! HÁ SOBREPOSIÇÕES. POR FAVOR, USUÁRIO: ' + USUARIO + ' ,CORRIGIR'
    else:
        co_overlap = 'NÃO HÁ SOBREPOSIÇÕES'
    return co_overlap

"""
MAPA GERAL CO + PT
"""

def __layout_map__(path_co, path_pt_shp):
    """
    LAYOUT GERAL DO MAPA CO + PT
    entrada -> shp contorno : requer um arquivo shp; shp pt -> requer um arquivo shp do tipo point
    :return: mapa
    """
    co = geopandas.read_file(path_co)  # CALL CO
    co.crs = "EPSG:4326"
    pt = geopandas.read_file(path_pt_shp)  # CALL PT
    pt.crs = "EPSG:4326"
    co_farm = co.plot(color='white', edgecolor='black', figsize=(15, 15))
    co_farm_pt = pt.plot(ax=co_farm, marker='o', color='red', markersize=5, figsize=(15, 15))
    # co_farm_pt.set_title('Relação Contorno e Pontos Totais')
    co_farm_pt.spines['top'].set_visible(False)
    co_farm_pt.spines['right'].set_visible(False)
    co_farm_pt.spines['left'].set_visible(False)
    # co_farm_pt.spines['bottom'].set_color(False)
    co_farm_pt.tick_params(bottom=False, left=False)
    co_farm_pt.set_axisbelow(False)
    co_farm_pt.yaxis.grid(False)
    co_farm_pt.xaxis.grid(False)
    co_farm_pt.grid(False)
    # Hide axes ticks
    co_farm_pt.set_xticks([])
    co_farm_pt.set_yticks([])
    layout_map_geral = fig2img(co_farm_pt)
    co_farm_pt.figure.savefig('download/layout_map.png', bbox_inches='tight')

    return layout_map_geral

"""
MAPA GERAL CO + JOIN
"""

def __map_join__(path, path_co, path_pt_shp, prof):
    """
    GERA OS JOIN CONFORME A PROFUNDIDADE ESPECIFICADA
    entrada -> shp contorno : requer um arquivo shp; shp pt -> requer um arquivo shp do tipo point f
    :return: resposta se há sobreposições
    """
    df_join_pt = __organization_df_to_shp__(path)
    co = geopandas.read_file(path_co)
    co.crs = "EPSG:4326"
    pt = geopandas.read_file(path_pt_shp)
    pt.crs = "EPSG:4326"
    pt_join_df = pt.merge(df_join_pt, on='ID', how='left')
    co_farm = co.plot(color='white', edgecolor='black', figsize=(15, 15))
    co_farm_pt_join = pt_join_df[pt_join_df.prof == prof].plot(ax=co_farm, marker='o', color='red', markersize=5,
                                                               figsize=(15, 15))
    co_farm_pt_join.set_title('Perfil - ' + prof)
    co_farm_pt_join.spines['top'].set_visible(False)
    co_farm_pt_join.spines['right'].set_visible(False)
    co_farm_pt_join.spines['left'].set_visible(False)
    # co_farm_pt.spines['bottom'].set_color(False)
    co_farm_pt_join.tick_params(bottom=False, left=False)
    co_farm_pt_join.set_axisbelow(False)
    co_farm_pt_join.yaxis.grid(False)
    co_farm_pt_join.xaxis.grid(False)
    co_farm_pt_join.grid(False)
    # Hide axes ticks
    co_farm_pt_join.set_xticks([])
    co_farm_pt_join.set_yticks([])

    return co_farm_pt_join

def __maps_join_dash__(path, path_pt_shp):
    pt = geopandas.read_file(path_pt_shp)
    df_join_pt = __organization_df_to_shp__(path)
    df_join_pt.rename(columns={'id': 'ID'}, inplace=True)
    pt.crs = "EPSG:4326"
    pt_join_df = pt.merge(df_join_pt, on='ID', how='left')

    return pt_join_df

def fig2img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it"""

    buf = io.BytesIO()
    fig.figure.savefig(buf, bbox_inches='tight')
    buf.seek(0)
    img = Image.open(buf)
    return img

def __export_map_perfil__(path, path_co, path_pt_shp):
    df = __organization_df__(path)
    prof_list = df.prof.unique().tolist()

    for profundidade in prof_list:
        a = __map_join__(path, path_co, path_pt_shp, profundidade)
        a.figure.savefig('download/' + profundidade + '.png', bbox_inches='tight')

def __png_perfil_png():
    png_list = []
    files = os.listdir('download/')
    for f in files:
        if 'CM.png' in f:
            png_list.append(f)
    return png_list

def __export_text_(path):
    df_dict = pd.read_excel(path, sheet_name=None, index_col=None)
    df_dict.pop('GERAL', None)

    return df_dict

def __shp_export__(path, path_pt_shp):
    pt = geopandas.read_file(path_pt_shp)
    df_join_pt = __organization_df_to_shp__(path)
    df_join_pt.rename(columns={'id': 'ID'}, inplace=True)
    pt.crs = "EPSG:4326"
    pt_join_df = pt.merge(df_join_pt, on='ID', how='left')
    return pt_join_df


def __duplicate_df__(path):
    ## CARREGAR EXCEL E REMOVER ABA GERAL
    try:
        df_dict = pd.read_excel(path, sheet_name=None, index_col=None)
        df_dict.pop('GERAL', None)
        ## SEPARA DATAFRAMES CONFORME A CHAVE PROFUNDIDADE
        df_list = []
        for key in df_dict:
            df_temp = df_dict[key]
            df_list.append(df_temp)

        duplicate_df = []

        for df in df_list:
            duplicate = df[df.duplicated(subset=['id'], keep=False)]
            duplicate.dropna(subset=['id'], inplace=True)
            duplicate = duplicate[['id', 'lab', 'lote', 'prof']]
            duplicate_df.append(duplicate)

        duplicate_df = [duplicate_df for duplicate_df in duplicate_df if not duplicate_df.empty]
        duplicate_df = pd.concat(duplicate_df)
    except ValueError:
        duplicate_df = pd.DataFrame(columns=['id', 'lab', 'lote', 'prof'])

    return duplicate_df

def ___without_join_df__(path, path_co, path_pt_shp):
    try:
        # df_join_pt=__organization_df_to_shp__(path)
        co = geopandas.read_file(path_co)  # CALL CO
        co.crs = "EPSG:4326"
        pt = geopandas.read_file(path_pt_shp)
        df_join_pt = __organization_df_to_shp__(path)
        df_join_pt.rename(columns={'id': 'ID'}, inplace=True)
        pt.crs = "EPSG:4326"
        without_join = pt.merge(df_join_pt, on='ID', how='left', indicator=True)
        out = pd.merge(pt, df_join_pt, how='outer', left_on=['ID'], right_on=['ID'], indicator=True).dropna(
            subset=['ID'])
        relation_out = out[['ID', 'lab', 'lote', 'prof', '_merge']]
        relation_out = relation_out.replace(to_replace="left_only", value="Pontos Sem Resultados")
        relation_out = relation_out.replace(to_replace="right_only", value="Resultados Sem Pontos")
        relation_out = relation_out.rename(columns={'_merge': 'Relação'})

        relation_out.drop(relation_out.index[(relation_out["Relação"] == "both")], axis=0, inplace=True)
    except ValueError:
        relation_out = pd.DataFrame(columns=['ID', 'lab', 'lote', 'prof', 'Relação'])

    return relation_out

def _pontos_fora__(path_co, path_pt_shp):
    co = geopandas.read_file(path_co)  # CALL CO
    co.crs = "EPSG:4326"
    pt = geopandas.read_file(path_pt_shp)
    pt.crs = "EPSG:4326"

    out = pt.sjoin(co, how='inner')
    out = out.rename(columns={'ID_left': 'ID'})
    out = out.merge(pt, on=['ID'], how='outer', suffixes=['', '_'], indicator=True)
    out.drop(out.index[(out["_merge"] == "both")], axis=0, inplace=True)
    id_out = out[['ID']]
    if id_out.empty == False:
        id_out_list_1 = id_out['ID'].astype(str).values.tolist()
        resposta_out = '!#ERROR#! Ponto(s): ' + ';'.join(id_out_list_1) + ' estão fora do polígono'
    else:
        resposta_out = ('')

    return resposta_out

def __remove_files():
    ## If file exists, delete it ##
    for i in os.listdir('download/'):
        try:

            if '.txt' in i:
                os.remove('download/' + i)
        except:
            pass

        try:
            if '.shz' in i:
                os.remove('download/' + i)
        except:
            pass

        try:
            if '.png' in i:
                os.remove('download/' + i)
        except:
            pass


def __frame__to_text(path_co):
    co = __polygon__(path_co)
    co_drop = co.drop('geometry', axis=1)
    co_text = co_drop.to_csv(sep=' ', index=False, header=False)
    return co_text

def detect_special_character(path_co):
    pass_string = __frame__to_text(path_co)

    regex = re.compile(r'[áéíóúâêîôãõçÁÉÍÓÚÂÊÎÔÃÕÇÑñ/\-!@#$%&*]')
    if (regex.search(pass_string) == None):
        res = str(False)
    else:
        res = str(True)

    return res

def __resposta_erro_text__(path_co):
    if detect_special_character(path_co) == 'True':
        resposta_erro_text = '!#ERROR#! Identificados Caracteres Especiais na Tabela de Atributos do Contorno: áéíóúâêîôãõçÁÉÍÓÚÂÊÎÔÃÕÇÑñ/\-!@#$%&*'
    else:
        resposta_erro_text = ''
    return resposta_erro_text

import datetime
from math import floor
from typing import Dict, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, \
    HTTP_404_NOT_FOUND, HTTP_418_IM_A_TEAPOT

from api.schemas.responses import HTTP_400_RESPONSE, HTTP_404_RESPONSE
from api.schemas.file_unit import UnitImportRequest, UnitSchema, \
    UnitStatisticResponse, UnitResponseSchema, HistoryRequest, HistoryResponseSchema, \
    TestSchema, UnitBaseSchema
from database.engine import get_session
from database.models import Unit, UnitType, HistoryUnit

router = APIRouter()

def unit_calc(unit: Unit):
    if unit.type == UnitType.FILE:
        return unit.size
    elif unit.type == UnitType.FOLDER:
        size = 0
        for child in unit.children:
            size += unit_calc(child)

        return size



@router.get('/', name='Test',tags=['Test'])
def get_test() -> Dict[str, str]:
    return {'Test': 'passed'}

@router.get('/brew_coffee', name='Test',tags=['Test'])
def get_test() -> Dict[str, str]:
    raise HTTPException(status_code=418, detail='I am a teapot.')


@router.post('/imports', name='Add new files and folders',
             status_code=200, tags=['Basic'])
def import_units(items: UnitImportRequest,
                 session: Session = Depends(get_session)) -> \
        Response:
    id_set = set()
    parent_set = set()
    file_set = set()

    for fileunit in items.items:

        if str(fileunit.id) in id_set:
            raise HTTPException(status_code=400, detail='id duplicate found!')
        id_set.add(str(fileunit.id))

        file_parent = session.query(Unit).filter(
            Unit.id == fileunit.parent_id).one_or_none()
        if file_parent is not None:
            if file_parent.type == UnitType.FILE:
                raise HTTPException(status_code=400, detail='parent id links to a file!')
        else:
            parent_set.add(str(fileunit.parent_id))

        if str(fileunit.type) == 'FILE':
            file_set.add(str(fileunit.type))

        fileunit.date = items.update_date
        file_unit_model = session.query(Unit).filter(
            Unit.id == fileunit.id).one_or_none()
        if file_unit_model is not None:
            if file_unit_model.type != fileunit.type:
                raise HTTPException(status_code=400, detail='Attempt to change unit type!')
            for var, value in vars(fileunit).items():
                setattr(file_unit_model, var, value)
            session.add(file_unit_model)
        else:
            session.add(Unit(**fileunit.dict()))
        if file_set & parent_set != set():
            raise HTTPException(status_code=400, detail='parent id links to a file!')
        if not (id_set >= parent_set):
            raise HTTPException(status_code=400, detail='parent id does not exist!')

        session.commit()
    date = items.update_date
    updated_units = session.query(Unit).filter(
        Unit.date == date).all()
    if updated_units:
        for unit in updated_units:
            dct = {}
            dct["id"] = str(unit.id)
            dct["type"] = str(unit.type).split('.')[1]
            dct["url"] = unit.url
            if not str(unit.parent_id) == "None":
                dct["parent_id"] = str(unit.parent_id)

            dct["size"] = unit_calc(unit)
            dct["date"] = str(unit.date.astimezone(datetime.timezone.utc))
            session.add(HistoryUnit(**dct))

        session.commit()

    return Response(status_code=200)


@router.get('/nodes/{id}',
            name='Get info about an element by id',
            response_model=UnitResponseSchema, response_model_by_alias=True,
            tags=['Basic'])

def get_unit(id:  str, session: Session = Depends(get_session)):
    unit = session.query(Unit).filter_by(id=id).one_or_none()
    if unit is None:
        raise HTTPException(status_code=404, detail='Item not found')
    element: UnitResponseSchema = UnitResponseSchema.from_orm(unit)
    if element.type == UnitType.FOLDER:
        stc = [[element, 0, 0]]
        while len(stc):
            last, index = stc[-1][0], stc[-1][1]
            child = last.get_child(index)
            if child is None:
                last.size = stc[-1][2]
                if len(stc) > 1:
                    stc[-2][2] += stc[-1][2]
                stc.pop()
            else:
                stc[-1][1] += 1
                if child.type == UnitType.FILE:
                    stc[-1][2] += child.size
                else:
                    stc.append([child, 0, 0])
    return element


@router.delete(
    '/delete/{id}',
    name='Remove an element by id',
    status_code=200,
    responses={
        200: {
            'description': 'The element was successfully removed',
            'model': None,
        },
        HTTP_400_BAD_REQUEST: HTTP_400_RESPONSE,
        HTTP_404_NOT_FOUND: HTTP_404_RESPONSE,
    },
    tags=['Basic']
)
def delete_unit(id: str,
                session: Session = Depends(get_session)) -> Response:

    unit = session.query(Unit).filter_by(id=id).one_or_none()
    if unit is None:
        raise HTTPException(status_code=404, detail='Item not found')
    try:
        session.delete(unit)
        session.commit()
        return Response(status_code=HTTP_200_OK)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail='Validation Failed')


@router.get('/updates', status_code=200, tags=['Advanced'],
            response_model=UnitStatisticResponse)
def get_files(date: datetime.datetime, session: Session = Depends(get_session)) -> UnitStatisticResponse:
    logger.info(date)
    items = session.query(Unit).filter(
        Unit.type == UnitType.FILE,
        Unit.date <= date,
        Unit.date >= date - datetime.timedelta(days=1),
    ).all()
    return UnitStatisticResponse(items=items)

@router.get('/node/{id}/history',
            name='History of updates for an element',
            response_model=HistoryResponseSchema, response_model_by_alias=True,
            tags=['Advanced'])

def get_history(id: str, dateStart: datetime.datetime = None, dateEnd: datetime.datetime = None, session: Session = Depends(get_session)):

    if dateStart == None:
        dateStart = datetime.datetime.min
    if dateEnd == None:
        dateEnd = datetime.datetime.max

    items = session.query(HistoryUnit).filter(
        HistoryUnit.id == id,
        HistoryUnit.date >= dateStart,
        HistoryUnit.date < dateEnd ).all()

    return {"items" : items}
